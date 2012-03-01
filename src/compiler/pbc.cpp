/*****************************************************************************
 *  Copyright (C) 2008-2011 Massachusetts Institute of Technology            *
 *                                                                           *
 *  Permission is hereby granted, free of charge, to any person obtaining    *
 *  a copy of this software and associated documentation files (the          *
 *  "Software"), to deal in the Software without restriction, including      *
 *  without limitation the rights to use, copy, modify, merge, publish,      *
 *  distribute, sublicense, and/or sell copies of the Software, and to       *
 *  permit persons to whom the Software is furnished to do so, subject       *
 *  to the following conditions:                                             *
 *                                                                           *
 *  The above copyright notice and this permission notice shall be included  *
 *  in all copies or substantial portions of the Software.                   *
 *                                                                           *
 *  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY                *
 *  KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE               *
 *  WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND      *
 *  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE   *
 *  LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION   *
 *  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION    *
 *  WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE           *
 *                                                                           *
 *  This source code is part of the PetaBricks project:                      *
 *    http://projects.csail.mit.edu/petabricks/                              *
 *                                                                           *
 *****************************************************************************/

#include "codegenerator.h"
#include "maximawrapper.h"
#include "transform.h"

#include "common/hash.h"
#include "common/jargs.h"
#include "common/jfilesystem.h"
#include "common/jtunable.h"
#include "common/openclutil.h"

#ifdef HAVE_CONFIG_H
#  include "config.h"
#endif


#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif


#include <fstream>
#include <iostream>
#include <sys/stat.h>
#include <sys/types.h>

const char headertxth[] = 
  "// Generated by " PACKAGE " compiler (pbc) v" VERSION " " REVISION_LONG "\n"
  "#include \"petabricks.h\"\n"
  "#ifdef __GNUC__\n"
  "#pragma GCC diagnostic ignored \"-Wunused-variable\"\n"
  "#pragma GCC diagnostic ignored \"-Wunused-parameter\"\n"
  "#pragma GCC diagnostic ignored \"-Wunused-value\"\n"
  "#endif\n"
  "using namespace petabricks;\n\n"
  ;

const char headertxtcpp[] = 
  "// Generated by " PACKAGE " compiler (pbc) v" VERSION " " REVISION_LONG "\n"
  "#include \""GENHEADER"\"\n"
  ;

using namespace petabricks;

namespace pbcConfig {
  bool shouldCompile = true;
  bool shouldLink = true;
  std::string theCommonDir;
  std::string theHardcodedConfig;
  std::string theInput;
  std::string theLibDir;
  std::string theMainName;
  std::string theObjDir;
  std::string theObjectFile;
  std::string theOutputBin;
  std::string theOutputInfo;
  std::string theRuntimeDir;
  std::string thePbPreprocessor;
  std::string theBasename;
  std::string theHeuristicsFile;
  std::string theKnowledgeBase;
  bool useDefaultHeuristics;
  int theNJobs = 2;
}
using namespace pbcConfig;

//defined in pbparser.ypp
TransformListPtr parsePbFile(const char* filename);

/* wrapper around popen */
FILE* opensubproc(const std::string& cmd) {
  FILE* p = popen((cmd+" 2>&1").c_str(), "r");
  JTRACE("calling gcc")(cmd);
  JASSERT(p!= 0)(cmd);
  return p;
}

/* wrapper around pclose */
void closesubproc(FILE* p, const std::string& name) {
  std::cerr << name << std::endl;
  while(!feof(p)) {
    char buf[1024];
    memset(buf, 0, sizeof buf);
    if(fread(buf, 1, sizeof buf -1,  p) > 0) {
      std::cerr << buf;
    }
  }
  JASSERT(pclose(p)==0);
}


/**
 * Small helper class used to output cpp files and call gcc
 */
class OutputCode {
  std::string   _cpp;
  std::string   _obj;
  StreamTreePtr _code;
  std::string   _gcccmd;
  FILE*         _gccfd;
public:
  OutputCode(const std::string& basename, CodeGenerator& o) 
    : _cpp(basename+".cpp")
    , _obj(basename+".o")
    , _gccfd(0)
  {
    _code = o.startSubfile(basename);

    std::ostringstream os; 
    os << CXX " " CXXFLAGS " " CXXDEFS " -c "
       << " -o "  << _obj 
       << " "     << _cpp
       << " -I\"" << theLibDir << "\""
       << " -I\"" << theRuntimeDir << "\"";
    _gcccmd = os.str();
  }

  void write() {
    std::ofstream of(_cpp.c_str());
    of << headertxtcpp;
    of << "/* Compile with: \n"
       <<  _gcccmd << "\n"
       << " */\n";
    _code->writeTo(of);
    of.flush();
    of.close();
  }

  void forkCompile() {
    JTRACE(_gcccmd.c_str());
    _gccfd = opensubproc(_gcccmd);
  }

  void waitCompile() {
    closesubproc(_gccfd, "Compile "+_cpp);
  }

  const std::string& objpath() const { return _obj; }

  void writeMakefile(std::ostream& o) {
    o << _obj << ": " << _cpp << "\n\t"
      << _gcccmd
      << "\n\n";
  }

};


/**
 * Collection of all the output source files of the compiler
 */
class OutputCodeList : public std::vector<OutputCode> {
public:
  void writeHeader(const StreamTreePtr& h) {
    std::ofstream of((theObjDir+"/"GENHEADER).c_str());
    h->writeTo(of);
    of.flush();
    of.close();
  }

  void write() {
    for(iterator i=begin(); i!=end(); ++i)
      i->write();
  }

  void compile() {
    iterator iwrite=begin(), ifork=begin(), iwait=begin();

    JASSERT(theNJobs>=1)(theNJobs);
    for(int i=0; i<theNJobs && iwait!=end(); ++i){
      if(iwrite!=end())
        (iwrite++)->write();
      if(ifork!=end())
        (ifork++)->forkCompile();
    }

    while(iwait!=end()) {
      //invariant: iwrite == ifork > iwait
      if(iwrite!=end())
        (iwrite++)->write();
      if(iwait!=end())
        (iwait++)->waitCompile();
      if(ifork!=end())
        (ifork++)->forkCompile();
    }
    JASSERT(iwrite==end());
    JASSERT(ifork==end());
  }

  std::string mklinkcmd() {
    std::ostringstream os; 
    os << CXX " -o " BIN_TMPFILE " " CXXFLAGS;
    for(const_iterator i=begin(); i!=end(); ++i)
      os << " " << i->objpath();
    os << " " CXXLDFLAGS " -L\"" << theLibDir <<"\" -lpbmain -lpbruntime -lpbcommon " CXXLIBS;
    return os.str();
  }

  void link() {
    JTRACE(mklinkcmd().c_str());
    closesubproc(opensubproc(mklinkcmd()), "Link "+theOutputBin);
  }
  
  void writeMakefile() {
    std::ofstream o("Makefile");
    o << "# Generated by " PACKAGE " compiler (pbc) v" VERSION " " REVISION_LONG "\n";
    o << "# This file is generated only for testing purposes and it not used\n\n";
    
    o << "all: " BIN_TMPFILE "\n\n";
    for(iterator i=begin(); i!=end(); ++i)
      i->writeMakefile(o);
    
    
    o << BIN_TMPFILE << ":";
    for(iterator i=begin(), e=end(); i!=e; ++i)
      o << " " << i->objpath();
    o << "\n\t" << mklinkcmd() << "\n\n";
    
    o << "clean_bin:\n";
    o << "\trm -f " BIN_TMPFILE "\n\n";
    
    o << "clean_obj:\n";
    o << "\trm -f *.o\n\n";
    
    o << "clean_temp:\n";
    o << "\trm -f *~ *.bak *.tmp *.temp\n\n";
    
    o << "clean: clean_bin clean_obj clean_temp\n";
  }
};

void loadDefaultHeuristics() {
  HeuristicManager& hm = HeuristicManager::instance();
  
  hm.registerDefault("UserRule_blockNumber", "2");
  hm.setMin("UserRule_blockNumber", 2);
  hm.setMax("UserRule_blockNumber", 15);
}

void findMainTransform(const TransformListPtr& t) {
  //find the main transform if it has not been specified
  if(theMainName==""){
    for(TransformList::const_iterator i=t->begin(); i!=t->end(); ++i){
      if((*i)->isMain()){
        JASSERT(theMainName=="")(theMainName)((*i)->name())
          .Text("Two transforms both have the 'main' keyword");
        theMainName = (*i)->name();
      }
    }
    if(theMainName=="") theMainName = t->back()->name();
  }
}

int main( int argc, const char ** argv){

  /*
  #ifdef HAVE_OPENCL
  OpenCLUtil::init();
  OpenCLUtil::printDeviceList();
  OpenCLUtil::deinit();
  exit(-1);
  #endif
  */

  // READ COMMAND LINE:

  OutputCodeList ccfiles;

  jalib::JArgs args(argc, argv);
  std::vector<std::string> inputs;
  if(args.needHelp())
    std::cerr << "OPTIONS:" << std::endl;
  
  thePbPreprocessor="\""PYTHON"\" \"" +
                    jalib::Filesystem::FindHelperUtility("preprocessor.py")
                    +"\"";

  args.param("input",      inputs).help("input file to compile (*.pbcc)");
  args.param("output",     theOutputBin).help("output binary to be produced");
  args.param("outputinfo", theOutputInfo).help("output *.info file to be produced");
  args.param("outputobj",  theObjectFile).help("output *.o file to be produced");
  args.param("runtimedir", theRuntimeDir).help("directory where petabricks.h may be found");
  args.param("libdir",     theLibDir).help("directory where libpbruntime.a may be found");
  args.param("preproc",    thePbPreprocessor).help("program to use as preprocessor");
  args.param("compile",    shouldCompile).help("disable the compilation step");
  args.param("link",       shouldLink).help("disable the linking step");
  args.param("main",       theMainName).help("transform name to use as program entry point");
  args.param("hardcode",   theHardcodedConfig).help("a config file containing tunables to set to hardcoded values");
  args.param("jobs",       theNJobs).help("number of gcc processes to call at once");
  args.param("heuristics", theHeuristicsFile).help("config file containing the (partial) set of heuristics to use");
  args.param("defaultheuristics", useDefaultHeuristics).help("use the default heuristics for every choice");
  args.param("knowledge", theKnowledgeBase).help("file containing the long-term learning knowledge base");
  
  if(args.param("version").help("print out version number and exit") ){
    std::cerr << PACKAGE " compiler (pbc) v" VERSION " " REVISION_LONG << std::endl;
    return 1;
  }

  args.finishParsing(inputs);

  if(inputs.empty() || args.needHelp()){
    std::cerr << "\n" PACKAGE " compiler (pbc) v" VERSION " " REVISION_SHORT << std::endl;
    std::cerr << "USAGE: " << argv[0] << " [OPTIONS] filename.pbcc" << std::endl;
    std::cerr << "run `" << argv[0] << " --help` for options" << std::endl;
    return 1;
  }

  JASSERT(inputs.size()==1)(inputs.size()).Text("expected exactly one input file");
  theInput = inputs.front();
  if(theRuntimeDir.empty()) theRuntimeDir = jalib::Filesystem::Dirname(jalib::Filesystem::FindHelperUtility("runtime/petabricks.h"));
  if(theLibDir    .empty()) theLibDir     = jalib::Filesystem::Dirname(jalib::Filesystem::FindHelperUtility("libpbruntime.a"));
  if(theOutputBin .empty()) theOutputBin  = jalib::Filesystem::Basename(theInput);
  if(theObjDir.empty())     theObjDir     = theOutputBin + ".obj";
  if(theOutputInfo.empty()) theOutputInfo = theOutputBin + ".info";
  if(theObjectFile.empty()) theObjectFile = theOutputBin + ".o";
  if(theKnowledgeBase.empty()) theKnowledgeBase = DBManager::defaultDBFileName();
  
  HeuristicManager::init(theKnowledgeBase);
  if(! theHeuristicsFile.empty()) HeuristicManager::instance().loadFromFile(theHeuristicsFile);
  if(useDefaultHeuristics) HeuristicManager::instance().useDefaultHeuristics(true);
  
  loadDefaultHeuristics();
  
  int rv = mkdir(theObjDir.c_str(), 0755);
  if(rv!=0 && errno==EEXIST)
    rv=0, errno=0;
  JASSERT(rv==0)(theObjDir).Text("failed to create objdir");
  
  if(!theHardcodedConfig.empty())
    CodeGenerator::theHardcodedTunables() = jalib::JTunableManager::loadRaw(theHardcodedConfig);

  JASSERT(jalib::Filesystem::FileExists(theInput))(theInput)
    .Text("input file does not exist");

  // PARSE:

  TransformListPtr t = parsePbFile(theInput.c_str());

  // COMPILE:

  for(TransformList::iterator i=t->begin(); i!=t->end(); ++i){
    (*i)->initialize();
    #ifdef DEBUG
    (*i)->print(std::cout);
    #endif
  }

  for(TransformList::iterator i=t->begin(); i!=t->end(); ++i){
    (*i)->compile();
  }

  findMainTransform(t);

  // CODEGEN:
  StreamTreePtr header = new StreamTree("header");
  StreamTreePtr prefix = header->add(new StreamTree("prefix"));
  CodeGenerator o(header, NULL);
  
  for(TransformList::iterator i=t->begin(); i!=t->end(); ++i){
    ccfiles.push_back(OutputCode((*i)->name(), o));
    (*i)->generateCode(o);
  }

  // generate misc files:
  o.cg().beginGlobal();
#ifdef SINGLE_SEQ_CUTOFF
  o.createTunable(true, "system.cutoff.sequential",  "sequentialcutoff", 64);
  o.createTunable(true, "system.cutoff.distributed", "distributedcutoff", 512);
#endif
  o.cg().addTunable(true, "system.runtime.threads", "worker_threads", 8, MIN_NUM_WORKERS, MAX_NUM_WORKERS);
#ifdef HAVE_OPENCL
  o.createTunable(true, "system.flag.localmem",  "use_localmem", 1, 0, 2);
  o.createTunable(true, "system.size.blocksize",  "opencl_blocksize", 16, 0, 25); // 0 means not using local memory
#endif
  o.cg().endGlobal();
  ccfiles.push_back(OutputCode(GENMISC, o));
  o.outputTunables(o.os());
  o.comment("A hook called by PetabricksRuntime");
  o.beginFunc("petabricks::PetabricksRuntime::Main*", "petabricksMainTransform");
  o.write("return "+theMainName+"_main::instance();");
  o.endFunc();
  o.comment("A hook called by PetabricksRuntime");
  o.beginFunc( "petabricks::PetabricksRuntime::Main*"
             , "petabricksFindTransform"
             , std::vector<std::string>(1, "const std::string& name"));
  for(TransformList::iterator i=t->begin(); i!=t->end(); ++i){
    (*i)->registerMainInterface(o);
  }
  o.write("return NULL;");
  o.endFunc();

  
  CodeGenerator& init    = o.forkhelper();
  CodeGenerator& cleanup = o.forkhelper();
  init.beginFunc("void", "_petabricksInit");
  cleanup.beginFunc("void", "_petabricksCleanup");
  for(TransformList::iterator i=t->begin(); i!=t->end(); ++i){
    (*i)->generateInitCleanup(init, cleanup);
  }
  init.endFunc();
  cleanup.endFunc();
  
  // generate common header file:
  *prefix << headertxth;
  *prefix << "namespace { \n";
  *prefix << CodeGenerator::theFilePrefix().str();
  *prefix << "} \n";
  o.outputTunableHeaders(*prefix);
  ccfiles.writeHeader(header);

  // dump .info file:
  std::ofstream infofile(theOutputInfo.c_str());
  o.cg().addHeuristics(HeuristicManager::instance().usedHeuristics());
  o.cg().addAllHeuristicFeatures(HeuristicManager::instance().usedHeuristics());
  o.cg().dumpTo(infofile);
  infofile.flush();
  infofile.close();


  char olddir[1024];
  memset(olddir, 0, sizeof olddir);
  JASSERT(olddir==getcwd(olddir, sizeof olddir - 1));
  JASSERT(chdir(theObjDir.c_str())==0)(theObjDir);
  
  ccfiles.writeMakefile();
  
  // COMPILE AND LINK:
  if(shouldCompile)
    ccfiles.compile();
  else
    ccfiles.write();

  if(shouldLink) {
    ccfiles.link();
    JASSERT(chdir(olddir)==0)(olddir);
    JASSERT(rename((theObjDir+"/"BIN_TMPFILE).c_str(), theOutputBin.c_str())==0)
      (theObjDir+"/"BIN_TMPFILE)(theOutputBin);
  }else{
    JASSERT(chdir(olddir)==0)(olddir);
  }


#ifdef DEBUG
  MAXIMA.sanityCheck();
#endif

  JTRACE("done")(theInput)(theOutputInfo)(theObjDir)(theOutputBin);
  return 0;
}


