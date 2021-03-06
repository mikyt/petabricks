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
#define _BSD_SOURCE

#include "jsocket.h"

#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <netdb.h>
#include <stdlib.h>
#include <strings.h>
#include <string.h>
#include <unistd.h>
#include "jassert.h"
#include <errno.h>
#include <algorithm>
#include <set>
#include <poll.h>

#ifdef HAVA_CONFIG_H
#  include "config.h"
#endif

#ifndef DMTCP
#  define DECORATE_FN(fn) ::fn
#else
#  include "syscallwrappers.h"
#  define DECORATE_FN(fn) ::_real_ ## fn
#endif

const jalib::JSockAddr jalib::JSockAddr::ANY ( NULL );

jalib::JSockAddr::JSockAddr ( const char* hostname )
{
  memset ( &_addr, 0, sizeof ( _addr ) );
  _addr.sin_family = AF_INET;
  if ( hostname == NULL )
  {
    _addr.sin_addr.s_addr = INADDR_ANY;
  }
  else
  {
    struct hostent *server = gethostbyname ( hostname );
    JWARNING ( server != NULL ) ( hostname ).Text ( "No such host" );
    if ( server != NULL )
    {
      JASSERT ( ( int ) sizeof ( _addr.sin_addr.s_addr ) <= server->h_length )
      ( sizeof ( _addr.sin_addr.s_addr ) )
      ( server->h_length );

      memcpy ( &_addr.sin_addr.s_addr,
               server->h_addr,
               server->h_length );
    }
  }
}

jalib::JSocket::JSocket()
{
  _sockfd = DECORATE_FN ( socket ) ( AF_INET, SOCK_STREAM, 0 );
}


bool jalib::JSocket::connect ( const JSockAddr& addr, int port )
{
  return JSocket::connect ( ( sockaddr* ) &addr._addr, sizeof ( addr._addr ), port );
}


bool jalib::JSocket::connect ( const  struct  sockaddr  *addr,  socklen_t addrlen, int port )
{
  union {
    struct sockaddr_storage addrbuf;
    struct sockaddr_in      addrbuf_in;
  };
  memset ( &addrbuf,0,sizeof ( addrbuf ) );
  JASSERT ( addrlen <= sizeof ( addrbuf ) ) ( addrlen ) ( sizeof ( addrbuf ) );
  memcpy ( &addrbuf,addr,addrlen );
  JWARNING ( addrlen == sizeof ( sockaddr_in ) ) ( addrlen ) ( sizeof ( sockaddr_in ) ).Text ( "may not be correct socket type" );
  addrbuf_in.sin_port = htons ( port );
  return DECORATE_FN ( connect ) ( _sockfd, ( sockaddr* ) &addrbuf, addrlen ) == 0;
}

bool jalib::JSocket::bind ( const JSockAddr& addr, int port )
{
  struct sockaddr_in addrbuf = addr._addr;
  addrbuf.sin_port = htons ( port );
  return bind ( ( sockaddr* ) &addrbuf, sizeof ( addrbuf ) );
}

bool jalib::JSocket::bind ( const  struct  sockaddr  *addr,  socklen_t addrlen )
{
  return DECORATE_FN ( bind ) ( _sockfd, addr, addrlen ) == 0;
}

bool jalib::JSocket::listen ( int backlog/* = 32*/ )
{
  return DECORATE_FN ( listen ) ( _sockfd, backlog ) == 0;
}

jalib::JSocket jalib::JSocket::accept ( struct sockaddr_storage* remoteAddr,socklen_t* remoteLen )
{
  if ( remoteAddr == NULL || remoteLen == NULL )
    return JSocket ( DECORATE_FN ( accept ) ( _sockfd,NULL,NULL ) );
  else
    return JSocket ( DECORATE_FN ( accept ) ( _sockfd, ( sockaddr* ) remoteAddr, remoteLen ) );
}

void jalib::JSocket::enablePortReuse()
{
  int one = 1;
  //These options will hopefully reduce address already in use errors
#ifdef SO_REUSEADDR
  if (setsockopt(_sockfd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one)) < 0){
    JWARNING(false)(JASSERT_ERRNO).Text("setsockopt(SO_REUSEADDR) failed");
  }
#endif
#ifdef SO_REUSEPORT
  if (setsockopt(_sockfd, SOL_SOCKET, SO_REUSEPORT, &one, sizeof(one)) < 0){
    JWARNING(false)(JASSERT_ERRNO).Text("setsockopt(SO_REUSEPORT) failed");
  }
#endif
}

void jalib::JSocket::disableNagle()
{
  int one = 1;
  if (setsockopt(_sockfd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one)) < 0){
    JWARNING(false)(JASSERT_ERRNO).Text("setsockopt(TCP_NODELAY) failed");
  }
}

bool jalib::JSocket::close()
{
  if ( !isValid() ) return false;
  int ret = DECORATE_FN(close) ( _sockfd );
  _sockfd = -1;
  return ret==0;
}

ssize_t jalib::JSocket::read ( char* buf, size_t len )
{
  return ::read ( _sockfd, buf,len );
}

ssize_t jalib::JSocket::tryReadAll ( char* buf, size_t len )
{
  // optimistically try a non-blocking read
  ssize_t rv = ::recv( _sockfd, buf, len, MSG_DONTWAIT);
  if(rv==0) {
    JTRACE("fallback case, got ambiguous read result");
    struct pollfd fd;
    fd.fd = _sockfd;
    fd.events = POLLIN;
    fd.revents = 0;
    if(poll(&fd, 1, 0) > 0) {
      JASSERT(fd.revents == POLLIN);
      rv += readAll(buf+rv, len-rv);
    }
  } else if(rv<0 && (errno == EWOULDBLOCK || errno == EINTR)) {
    rv = 0;
  } else if(0<rv && rv<(ssize_t)len) {
    JTRACE("fallback case, got only part of requested data")(rv)(len);
    rv += readAll(buf+rv, len-rv);
  }
  return rv;
}

ssize_t jalib::JSocket::write ( const char* buf, size_t len )
{
  return ::write ( _sockfd, buf,len );
}

ssize_t jalib::JSocket::readAll( char* buf, size_t len )
{
  ssize_t rv = ::recv( _sockfd, buf,len, MSG_WAITALL);
  if(rv<0 && (errno == EWOULDBLOCK || errno == EINTR)) {
    rv = 0;
  }
  if(0<=rv && rv<(ssize_t)len) {
    JTRACE("fallback");
    rv += readAllFallback(buf+rv, len-rv);
  }
  return rv;
}

ssize_t jalib::JSocket::readAllFallback ( char* buf, size_t len )
{
  int origLen = len;
  while ( len > 0 )
  {
    fd_set rfds;
    struct timeval tv;
    int retval;

    /* Watch stdin (fd 0) to see when it has input. */
    FD_ZERO ( &rfds );
    FD_SET ( _sockfd, &rfds );

    tv.tv_sec = 120;
    tv.tv_usec = 0;

    retval = select ( _sockfd+1, &rfds, NULL, NULL, &tv );
    /* Don't rely on the value of tv now! */


    if ( retval == -1 )
    {
      JWARNING ( retval >= 0 ) ( _sockfd ) ( JASSERT_ERRNO ).Text ( "select() failed" );
      return -1;
    }
    else if ( retval )
    {
      ssize_t cnt = read ( buf, len );
      if ( cnt <= 0 && errno != EAGAIN && errno != EINTR )
      {
        JWARNING(cnt>0)(sockfd())(cnt)(len)(JASSERT_ERRNO).Text( "JSocket read failure" );
        return -1;
      }
      if ( cnt > 0 )
      {
        buf += cnt;
        len -= cnt;
      }
    }
    else
    {
      JTRACE ( "still waiting for data" ) ( _sockfd ) ( len );
    }
  }
  return origLen;
}

ssize_t jalib::JSocket::writeAll( const char* buf, size_t len )
{
  ssize_t rv = ::write( _sockfd, buf,len);
  if(rv<0 && (errno == EWOULDBLOCK || errno == EINTR)) {
    rv = 0;
  }
  if(0<=rv && rv<(ssize_t)len) {
    JTRACE("fallback");
    rv += writeAllFallback(buf+rv, len-rv);
  }
  return rv;
}

ssize_t jalib::JSocket::writeAllFallback ( const char* buf, size_t len )
{
  int origLen = len;
  while ( len > 0 )
  {
    fd_set wfds;
    struct timeval tv;
    int retval;

    /* Watch stdin (fd 0) to see when it has input. */
    FD_ZERO ( &wfds );
    FD_SET ( _sockfd, &wfds );

    /* Wait up to five seconds. */
    tv.tv_sec = 30;
    tv.tv_usec = 0;

    retval = select ( _sockfd+1, NULL, &wfds, NULL, &tv );
    /* Don't rely on the value of tv now! */


    if ( retval == -1 )
    {
      JWARNING ( retval >= 0 ) ( _sockfd ) ( JASSERT_ERRNO ).Text ( "select() failed" );
      return -1;
    }
    else if ( retval )
    {
      ssize_t cnt = write ( buf, len );
      if ( cnt <= 0 && errno != EAGAIN && errno != EINTR )
      {
        JWARNING ( cnt > 0 ) ( cnt ) ( len ) ( JASSERT_ERRNO ).Text ( "JSocket read failure" );
        return -1;
      }
      if ( cnt > 0 )
      {
        buf += cnt;
        len -= cnt;
      }
    }
    else
    {
      JTRACE ( "still waiting for data" ) ( _sockfd ) ( len );
    }
  }
  return origLen;
}

bool jalib::JSocket::isValid() const
{
  return _sockfd >= 0;
}




/*!
    \fn jalib::JChunkReader::readAvailable()
 */
bool jalib::JChunkReader::readOnce()
{
  if ( !ready() )
  {
    ssize_t cnt = _sock.read ( _buffer + _read, _length - _read );
    if ( cnt <= 0 && errno != EAGAIN && errno != EINTR )
      _hadError = true;
    if ( cnt > 0 )
      _read += cnt;
  }
  return ready();
}

/*!
    \fn jalib::JChunkWriter::isDone()
 */
bool jalib::JChunkWriter::isDone()
{
  return _length <= _sent;
}


/*!
    \fn jalib::JChunkWriter::writeOnce()
 */
bool jalib::JChunkWriter::writeOnce()
{
  if ( !isDone() )
  {
    ssize_t cnt = _sock.write ( _buffer + _sent, _length - _sent );
    if ( cnt <= 0 && errno != EAGAIN && errno != EINTR )
      _hadError = true;
    if ( cnt > 0 )
      _sent += cnt;
  }
  return isDone();
}


/*!
    \fn jalib::JChunkWriter::hadError()
 */
bool jalib::JChunkWriter::hadError()
{
  return _hadError || !_sock.isValid();
}



/*!
    \fn jalib::JChunkReader::reset()
 */
void jalib::JChunkReader::reset()
{
  memset ( _buffer,0,_length );
  _read = 0;
}


/*!
    \fn jalib::JChunkReader::readAll()
 */
void jalib::JChunkReader::readAll()
{
  while ( !ready() ) readOnce();
}

/*!
    \fn jalib::JChunkReader::JChunkReader(JSocket sock, int chunkSize);
 */
jalib::JChunkReader::JChunkReader ( JSocket sock, int chunkSize )
    : JReaderInterface ( sock )
    , _buffer ( new char[chunkSize] )
    , _length ( chunkSize )
    , _read ( 0 )
    , _hadError ( false )
{
  memset ( _buffer,0,_length );
}


/*!
    \fn jalib::JChunkReader::JChunkReader(const JChunkReader& that)
 */
jalib::JChunkReader::JChunkReader ( const JChunkReader& that )
    : JReaderInterface ( that )
    , _buffer ( new char[that._length] )
    , _length ( that._length )
    , _read ( that._read )
    , _hadError ( that._hadError )
{
  memcpy ( _buffer,that._buffer,_length );
}


/*!
    \fn jalib::JChunkReader::~JChunkReader()
 */
jalib::JChunkReader::~JChunkReader()
{
  delete [] _buffer;
  _buffer = 0;
}


/*!
    \fn jalib::JChunkReader::operator=(const JChunkReader& that)
 */
jalib::JChunkReader& jalib::JChunkReader::operator= ( const JChunkReader& that )
{
  if ( this == &that ) return *this;;
  delete [] _buffer;
  _buffer = 0;
  new ( this ) JChunkReader ( that );
  return *this;
}




/*!
    \fn jalib::JSocket::changeFd(int newFd)
 */
void jalib::JSocket::changeFd ( int newFd )
{
  if ( _sockfd == newFd ) return;
  JASSERT ( newFd == DECORATE_FN(dup2) ( _sockfd, newFd ) ) 
      ( _sockfd ) ( newFd ).Text ( "dup2 failed" );
  close();
  _sockfd = newFd;
}


void jalib::JMultiSocketProgram::addDataSocket ( JReaderInterface* sock )
{
  _dataSockets.push_back ( sock );
}

void jalib::JMultiSocketProgram::addListenSocket ( const JSocket& sock )
{
  _listenSockets.push_back ( sock );
}


void jalib::JMultiSocketProgram::addWrite ( JWriterInterface* write )
{
  _writes.push_back ( write );
}

void jalib::JMultiSocketProgram::monitorSockets ( double dblTimeout )
{
  int tSec = ( int ) dblTimeout;
  int tMs = ( int ) ( 1000000.0 * ( dblTimeout - tSec ) );
  const struct timeval timeoutInterval = {tSec,tMs};
  bool timeoutEnabled = dblTimeout > 0 && timerisset ( &timeoutInterval );

  struct timeval stoptime={0,0};
  struct timeval tmptime={0,0};
  struct timeval timeoutBuf=timeoutInterval;
  struct timeval * timeout = timeoutEnabled ? &timeoutBuf : NULL;
  JASSERT ( gettimeofday ( &stoptime,NULL ) ==0 );
  timeradd ( &timeoutInterval,&stoptime,&stoptime );

  std::set<int> closedFds;
  fd_set rfds;
  fd_set wfds;
  int maxFd;
  size_t i;
  for ( ;; )
  {
    closedFds.clear();
    maxFd = -1;
    FD_ZERO ( &rfds );
    FD_ZERO ( &wfds );

    //collect listen fds in rfds, cleanup dead sockets
    for ( i=0; i<_listenSockets.size(); ++i )
    {
      if ( _listenSockets[i].isValid() )
      {
        FD_SET ( _listenSockets[i].sockfd(), &rfds );
        maxFd = std::max ( maxFd,_listenSockets[i].sockfd() );
      }
      else
      {
        _listenSockets[i].close();
        //socket is dead... remove it
        JTRACE ( "listen socket failure" ) ( i );
        //swap with last
        _listenSockets[i] = _listenSockets[_listenSockets.size()-1];
        _listenSockets.pop_back();
        i--;
      }
    }

    //collect data fds in rfds, cleanup dead sockets
    for ( i=0; i<_dataSockets.size(); ++i )
    {
      if ( !_dataSockets[i]->hadError() )
      {
        FD_SET ( _dataSockets[i]->socket().sockfd(), &rfds );
        maxFd = std::max ( maxFd,_dataSockets[i]->socket().sockfd() );
      }
      else
      {
        closedFds.insert(_dataSockets[i]->socket().sockfd());
        //socket is dead... remove it
        //JTRACE ( "disconnect" ) ( i ) ( _dataSockets[i]->socket().sockfd() );
        onDisconnect ( _dataSockets[i] );
        _dataSockets[i]->socket().close();
        delete _dataSockets[i];
        _dataSockets[i] = 0;
        //swap with last
        _dataSockets[i] = _dataSockets[_dataSockets.size()-1];
        _dataSockets.pop_back();
        i--;
      }
    }

    //collect all writes in wfds, cleanup finished/dead
    for ( i=0; i<_writes.size(); ++i )
    {
      if (  !_writes[i]->hadError() 
         && !_writes[i]->isDone() 
         && closedFds.find(_writes[i]->socket().sockfd())==closedFds.end() )
      {
        FD_SET ( _writes[i]->socket().sockfd(), &wfds );
        maxFd = std::max ( maxFd,_writes[i]->socket().sockfd() );
      }
      else
      {
        //socket is or write done... pop it
        delete _writes[i];
        _writes[i] = 0;
        //swap with last
        _writes[i] = _writes[_writes.size()-1];
        _writes.pop_back();
        i--;
      }
    }

    if ( maxFd == -1 )
    {
      //JTRACE ( "no sockets left" );
      return;
    }

    //this will block till we have some work to do
    int retval = select ( maxFd+1, &rfds, &wfds, NULL, timeout );

    if ( retval == -1 )
    {
      JWARNING ( retval != -1 ) ( maxFd ) ( retval ) ( JASSERT_ERRNO ).Text ( "select failed" );
      return;
    }
    else if ( retval > 0 )
    {

      //write all data
      for ( i=0; i<_writes.size(); ++i )
      {
        int fd = _writes[i]->socket().sockfd();
        if ( fd >= 0 && FD_ISSET ( fd, &wfds ) )
        {
//                    JTRACE("writing data")(_writes[i]->socket().sockfd());
          _writes[i]->writeOnce();
        }
      }


      //read all new data
      for ( i=0; i<_dataSockets.size(); ++i )
      {
        int fd = _dataSockets[i]->socket().sockfd();
        if ( fd >= 0 && FD_ISSET ( fd, &rfds ) )
        {
//                   JTRACE("recieving data")(i)(_dataSockets[i].socket().sockfd());
          if ( _dataSockets[i]->readOnce() )
          {
            onData ( _dataSockets[i] );
            _dataSockets[i]->reset();
          }
        }
      }


      //accept all new connections
      for ( i=0; i<_listenSockets.size(); ++i )
      {
        int fd = _listenSockets[i].sockfd();
        if ( fd >= 0 && FD_ISSET ( fd, &rfds ) )
        {
          struct sockaddr_storage addr;
          socklen_t               addrlen=sizeof ( addr );
          JSocket sk = _listenSockets[i].accept ( &addr,&addrlen );
          JTRACE ( "accepting new connection" ) ( i ) ( sk.sockfd() ) ( _listenSockets[i].sockfd() ) ( errno );
          if ( sk.isValid() )
          {
            onConnect ( sk, ( sockaddr* ) &addr,addrlen );
          }
          else if ( errno != EAGAIN && errno != EINTR )
          {
            _listenSockets[i].close();
          }
        }
      }



    }

    if ( timeoutEnabled )
    {
      JASSERT ( gettimeofday ( &tmptime,NULL ) ==0 );
      if ( timercmp ( &tmptime, &stoptime, < ) )
      {
        timersub ( &stoptime, &tmptime, &timeoutBuf );
      }
      else
      {
        timeoutBuf = timeoutInterval;
        stoptime = tmptime;
        timeradd ( &timeoutInterval,&stoptime,&stoptime );
//                 JTRACE("timeout interval")(timeoutSec);
        onTimeoutInterval();
      }
    }
  }
}





/*!
    \fn jalib::JChunkWriter::JChunkWriter(JSocket sock, const char* buf, int len)
 */
jalib::JChunkWriter::JChunkWriter ( JSocket sock, const char* buf, int len )
    :JWriterInterface ( sock )
    ,_buffer ( new char [len] )
    ,_length ( len )
    ,_sent ( 0 )
    ,_hadError ( false )
{
  memcpy ( _buffer,buf,len );
}


/*!
    \fn jalib::JChunkWriter::JChunkWriter(const JChunkWriter& that)
 */
jalib::JChunkWriter::JChunkWriter ( const JChunkWriter& that )
    :JWriterInterface ( that )
    ,_buffer ( new char [that._length] )
    ,_length ( that._length )
    ,_sent ( that._sent )
    ,_hadError ( false )
{
  memcpy ( _buffer,that._buffer,that._length );
}


/*!
    \fn jalib::JChunkWriter::~JChunkWriter()
 */
jalib::JChunkWriter::~JChunkWriter()
{
  delete [] _buffer;
  _buffer = 0;
}


/*!
    \fn jalib::JChunkWriter::method_4()
 */
jalib::JChunkWriter& jalib::JChunkWriter::operator= ( const JChunkWriter& that )
{
  if ( this == &that ) return *this;;
  delete [] _buffer;
  _buffer = 0;
  new ( this ) JChunkWriter ( that );
  return *this;
}


