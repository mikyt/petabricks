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
#ifdef HAVE_CONFIG_H
# include "config.h"
#endif

#ifdef HAVE_OPENCL

#include "clcodegenerator.h"

namespace petabricks
{

void
CLCodeGenerator::outputStringTo( std::ostream& o )
{
  o << os().str( );
}

void
CLCodeGenerator::outputEscapedStringTo( std::ostream& o )
{
  std::string str = os().str();

  o << "\"";
  for( std::string::const_iterator it = str.begin( ); it != str.end( ); ++it )
      switch( *it )
	{
	case '\\':
	  o << "\\\\";
	  break;
	case '"':
	  o << "\\\"";
	  break;
	case '\n':
	  //o << "\\n";
	  o << "\\n\"\n\"";
	  break;
	case '\t':
	  o << "\\t";
	  break;
	default:
	  o << *it;
	  break;
	}
  o << "\"";
  return;
}

std::string
CLCodeGenerator::outputEscapedString( )
{
  std::stringstream ss;
  outputEscapedStringTo( ss );
  return ss.str( );
}

void
CLCodeGenerator::localMemoryBarrier( )
{
  os() << "barrier( CLK_LOCAL_MEM_FENCE );\n";
}

void CLCodeGenerator::beginKernel(RegionList& _to, RegionList& _from, unsigned int dims)
{

  os() << "__kernel void kernel_main( ";

  // The kernel will need a pointer to an appropriate chunk of each input and output matrix
  for(RegionList::const_iterator it = _to.begin(); it != _to.end(); ++it)
  {
    if( it != _to.begin() )
	    os() << ", ";
    os() << "__global " << STRINGIFY(MATRIX_ELEMENT_T) << "* _region_" << (*it)->name();
  }
  for(RegionList::const_iterator it = _from.begin(); it != _from.end(); ++it)
  { 
    os() << ", __global " << STRINGIFY(MATRIX_ELEMENT_T) << "* _region_" << (*it)->name();
  }

  // And we'll need to provide the size of the region that we want the kernel to operate on.  (This is where the 'center' of the rule will be.)
  for( int i = 0; i < (int)dims; ++i )
  {
    os() << ", int dim_d" << i;
    //os() << ", int dim_d" << i << "_begin";
    //os() << ", int dim_d" << i << "_end";
  }

  //TODO: using _to and_from is the correct approach
  // Finally, we need to provide some of the dimensions of each of the matrices we've passed in, so that we can calculate indices.
  for(RegionList::const_iterator it = _to.begin(); it != _to.end(); ++it)
  {
    for( int i = 0; i < (int) (*it)->size() - 1 ; ++i )
	    os() << ", int dim_" << (*it)->name() << "_d" << i;
  }
  for(RegionList::const_iterator it = _from.begin(); it != _from.end(); ++it)
  {
    for( int i = 0; i < (int) (*it)->size() - 1 ; ++i )
	    os() << ", int dim_" << (*it)->name() << "_d" << i;
  }

  os() << " ) {\n";
}

void
CLCodeGenerator::endKernel( )
{
  os() << "}\n";
}

}

#endif
