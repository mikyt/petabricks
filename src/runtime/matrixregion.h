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
#ifndef PETABRICKSMATRIX_H
#define PETABRICKSMATRIX_H

#include "matrixstorage.h"
#include "common/hash.h"

#include <stdarg.h>
#include <stdio.h>

//
// Class structure looks like this:
//
//  MatrixRegion  (specialized for MatrixRegion0D and  ConstMatrixRegion0D)
//    extends 
//  MatrixRegionVaArgsMethods (specialized a lot, for performance only; GCC optimizes VA_ARGS poorly)
//    extends
//  MatrixRegionBasicMethods
//    extends
//  MatrixRegionMembers (specialized for ConstMatrixRegion0D)
//
// Specializations can be found in matrixspecializations.h
//
// Now the main classes in reverse order of whats listed above:
//

namespace petabricks {

template< int D, typename ElementT> class MatrixRegion;

//trick to break the cycle for SliceMatrixRegion going to MatrixRegion<-1>
template<int _D> struct _slicesize    { enum { D = _D-1 }; };
template< >      struct _slicesize<0> { enum { D = 0    }; };

/**
 * We have divided MatrixRegion into many smaller classes (combined through a chain of inheritance)
 * so that small parts may easily be specialized.
 *
 * This part defines some typedefs and simplifies the template args for the rest of the classes.
 */
template< int _D, typename _ElementT >
struct MatrixRegionTypeSpec {
  enum { D = _D };
  typedef _ElementT ElementT;
  typedef MATRIX_INDEX_T IndexT;
  typedef petabricks::MatrixStoragePtr StorageT;
  typedef petabricks::MatrixRegion<_slicesize<D>::D, ElementT> SliceMatrixRegion;
  typedef petabricks::MatrixRegion<D, MATRIX_ELEMENT_T> MutableMatrixRegion;
  typedef petabricks::MatrixRegion<D, ElementT>         MatrixRegion;
};

/**
 * We have divided MatrixRegion into many smaller classes (combined through a chain of inheritance)
 * so that small parts may easily be specialized.
 *
 * This part contains the member variables and storage.
 */
template< typename TypeSpec >
class MatrixRegionMembers {
public:
  enum { D = TypeSpec::D };
  typedef typename TypeSpec::StorageT StorageT;
  typedef typename TypeSpec::IndexT   IndexT;
  typedef typename TypeSpec::ElementT ElementT;
  
  ///
  /// Constructor
  MatrixRegionMembers(const StorageT& s, ElementT* b, const IndexT RESTRICT* sizes, const IndexT RESTRICT * multipliers)
    : _storage(s), _base(b)
  {
    if(D>0) {
      const size_t sizeof_sizes = sizeof this->_sizes;
      const size_t sizeof_multipliers = sizeof this->_sizes;

      if(multipliers != NULL)
        memcpy(this->_multipliers, multipliers, sizeof_multipliers );
      else
        memset(this->_multipliers, 0, sizeof_multipliers);

      if(sizes != NULL)
        memcpy(this->_sizes, sizes, sizeof_sizes);
      else
        memset(this->_sizes, -1, sizeof_sizes);
    }
  }
  
  ElementT* base() const { return _base; }
  const IndexT* sizes() const { return _sizes; }
  const IndexT* multipliers() const { return _multipliers; };
  const StorageT& storage() const { return _storage; }

  void randomize(){
    if(D==0){
      //0D version may not use storage(), so just set the element directly
      JASSERT(base()!=0);
      *const_cast<MATRIX_ELEMENT_T*>(base()) = MatrixStorage::rand();
    }else{
      this->storage()->randomize();
    }
  }

  ///
  /// export to a more generic container (used in memoization)
  void exportTo(MatrixStorageInfo& ms) const {
    ms.setStorage(_storage, _base);
    ms.setSizeMultipliers(D, _multipliers, _sizes);
    ms.setExtraVal();
  }
  
  ///
  /// copy from a more generic container (used in memoization)
  void copyFrom(const MatrixStorageInfo& ms){
    JASSERT(_base!=0);
    if(ms.storage()!=storage()){
      JASSERT(ms.storage()->count()==storage()->count());
      memcpy(storage()->data(), ms.storage()->data(), storage()->count()*sizeof(ElementT));
    }
  }
protected: 
  IndexT* sizes() { return _sizes; }
  IndexT* multipliers() { return _multipliers; };
private:
  StorageT _storage;
  ElementT* _base;
  IndexT _multipliers[D];
  IndexT _sizes[D];
};

/**
 * We have divided MatrixRegion into many smaller classes (combined through a chain of inheritance)
 * so that small parts may easily be specialized.
 *
 * This part contains most methods.
 */
template< typename TypeSpec >
class MatrixRegionBasicMethods : public MatrixRegionMembers< TypeSpec > {
public:
  typedef MatrixRegionMembers< TypeSpec > Base;
  MatrixRegionBasicMethods( const typename TypeSpec::StorageT& s
                          , typename TypeSpec::ElementT* b
                          , const typename TypeSpec::IndexT* sizes
                          , const typename TypeSpec::IndexT* multipliers)
    : Base(s,b,sizes,multipliers)
  {}

  enum StockLayouts { LAYOUT_ASCENDING, LAYOUT_DECENDING };
  enum { D = TypeSpec::D };
  typedef typename TypeSpec::StorageT            StorageT;
  typedef typename TypeSpec::IndexT              IndexT;
  typedef typename TypeSpec::ElementT            ElementT;
  typedef typename TypeSpec::MatrixRegion        MatrixRegion;
  typedef typename TypeSpec::SliceMatrixRegion   SliceMatrixRegion;
  typedef typename TypeSpec::MutableMatrixRegion MutableMatrixRegion;
  
  ///
  /// Allocate a storage for a new MatrixRegion
  static MatrixRegion allocate(const IndexT sizes[D]) {
    ssize_t s=1;
    for(int i=0; i<D; ++i)
      s*=sizes[i];
    MatrixStoragePtr tmp = new MatrixStorage(s);
    #ifdef DEBUG
    //in debug mode initialize matrix to garbage
    for(int i=0; i<s; ++i)
      tmp->data()[i] = -666;
    #endif
    return MatrixRegion(tmp, tmp->data(), sizes);
  }
  
  ///
  ///same as allocate unless this->sizes()==sizes
  bool isSize(const IndexT sizes[D]) const{
    if(this->base()==0) return false;
    for(int i=0; i<D; ++i){
      if(this->sizes()[i]!=sizes[i]){
        return false;
      }
    }
    return true;
  }
  bool isSize(IndexT x, ...) const{
    IndexT c1[D];
    va_list ap;
    va_start(ap, x);
    c1[0]=x;
    for(int i=1; i<D; ++i) c1[i]=va_arg(ap, IndexT);
    va_end(ap);
    return isSize(c1);
  }

  ///
  ///Return an iterator that accesses elements in a transposed fashion
  MatrixRegion transposed() const {
    IndexT sizes[D];
    IndexT multipliers[D];
    for(int i=0; i<D; ++i){
      sizes[i]       = this->sizes()[D-i-1];
      multipliers[i] = this->multipliers()[D-i-1];
    }
    return MatrixRegion(this->storage(), this->base(), sizes, multipliers);
  }

  ///
  /// A region is considered normalized if it occupies the entire buffer and is organized so that
  /// a N-dimensional buffer is laid out as sequential (N-1)-dimensional buffers.
  MatrixRegion asNormalizedRegion( bool copyData = true ) const
  {
    if( isEntireBuffer( ) )
      return MatrixRegion(this->storage(), this->base(), this->sizes(), this->multipliers());

    MutableMatrixRegion t = MutableMatrixRegion::allocate((IndexT*)this->sizes());
    if( copyData ) {
      IndexT coord[D];
      memset(coord, 0, sizeof coord);
      do {
        t.cell(coord) = this->cell(coord);
      } while(this->incCoord(coord)>=0);
    }
    return t;
  }
  
  ///
  /// Copy that data of this to dst
  void copyTo(const MutableMatrixRegion& dst)
  {
    if(this->base() == dst.base())
      return;
    JASSERT(this->count()==dst.count());
    IndexT coord[D];
    memset(coord, 0, sizeof coord);
    do {
      dst.cell(coord) = this->cell(coord);
    } while(this->incCoord(coord)>=0);
  }

  ///
  /// Access a single cell of target matrix
  INLINE ElementT& cell(const IndexT c1[D]) const{ return *this->coordToPtr(c1); }

  ///
  /// Create a new iterator for a region of target matrix
  MatrixRegion region(const IndexT c1[D], const IndexT c2[D]) const{
    IndexT newSizes[D];
    for(int i=0; i<D; ++i){
      #ifdef DEBUG
      JASSERT(c1[i]<=c2[i])(c1[i])(c2[i])
        .Text("region has negative size");
      JASSERT(c2[i]<=size(i))(c2[i])(size(i))
        .Text("region goes out of bounds");
      #endif
      newSizes[i]=c2[i]-c1[i];
    }
    return MatrixRegion(this->storage(), this->coordToPtr(c1), newSizes, this->multipliers());
  }

  ///
  /// Return a slice through this dimension
  /// The iterator is one dimension smaller and equivilent to always 
  /// giving pos for dimension d
  SliceMatrixRegion slice(int d, IndexT pos) const{
    #ifdef DEBUG
    JASSERT(d>=0 && d<D)(d).Text("invalid dimension");
    JASSERT(pos>=0 && pos<size(d))(pos)(size(d)).Text("out of bounds access");
    #endif
    IndexT sizes[D-1];
    IndexT mult[D-1];
    for(int i=0; i<d; ++i){
        sizes[i] = this->sizes()[i];
        mult[i]  = this->multipliers()[i];
    }
    for(int i=d+1; i<D; ++i){
        sizes[i-1] = this->sizes()[i];
        mult[i-1]  = this->multipliers()[i];
    }
    IndexT coord[D];
    memset(coord, 0, sizeof coord);
    coord[d] = pos;
    return SliceMatrixRegion(this->storage(), this->coordToPtr(coord), sizes, mult);
  }
  
  
  SliceMatrixRegion col(IndexT x) const{ return slice(0, x); }
  SliceMatrixRegion column(IndexT x) const{ return slice(0, x); }
  SliceMatrixRegion row(IndexT y) const{  return slice(1, y); }
  
  ///
  /// true if c1 is in bounds
  bool contains(const IndexT coord[D]) const { 
    for(int i=0; i<D; ++i)
      if(coord[i]<0 || coord[i]>=size(i))
        return false;
    return true;
  }
  
  ///
  /// Return the size of a given dimension
  IndexT size(int d) const {
    #ifdef DEBUG
    JASSERT(d>=0 && d<D)(d)((int)D);
    #endif
    return this->sizes()[d];
  }


  IndexT width() const { return size(0); }
  IndexT height() const { return size(1); }
  IndexT depth() const { return size(2); }
  MatrixRegion all() const { return MatrixRegion(this->storage(), this->base(), this->sizes(), this->multipliers()); }

  ///
  /// Number of elements in this region
  ssize_t count() const {
    ssize_t s=1;
    for(int i=0; i<D; ++i)
      s*=this->sizes()[i];
    return s;
  }

  ///
  /// sum of the sizes in each dimension
  IndexT perimeter() const {
    IndexT s=0;
    for(int i=0; i<D; ++i)
      s+=this->sizes()[i];
    return s;
  }

  ///
  /// Number of bytes taken to store the elements in this region
  ssize_t bytes() const {
    return count()*sizeof(ElementT);
  }
  
  ///
  /// force this region to be a mutable type (removes constness)
  /// this is evil
  MutableMatrixRegion forceMutable() {
    return MutableMatrixRegion(
        this->storage(),
        (MATRIX_ELEMENT_T*) this->base(),
        this->sizes(),
        this->multipliers());
  }

  ///
  /// true if this region occupies the entire buffer _storage
  bool isEntireBuffer() const {
    if(D==0) return true;
    return this->storage() && (ssize_t)this->storage()->count()==count();
  }

  ///
  /// increment a raw coord in ascending order
  /// return largest dimension incremented or -1 for end
  int incCoord(IndexT coord[D]) const{
    if(D==0) 
     return -1;
    int i;
    coord[0]++;
    for(i=0; i<D-1; ++i){
      if(coord[i] >= this->size(i)){
        coord[i]=0;
        coord[i+1]++;
      }else{
        return i;
      }
    }
    if(coord[D-1] >= this->size(D-1)){
      return -1;
    }else{
      return D-1;
    }
  }

  ///
  /// hash the content of this to gen
  void hash(jalib::HashGenerator& gen) const{
    if(this->count()>0){
      IndexT coord[D];
      memset(coord, 0, sizeof coord);
      do {
        gen.update(this->coordToPtr(coord), sizeof(ElementT));
      } while(this->incCoord(coord)>=0);
    }
  }
  
protected:
  ///
  /// Compute the offset in _base for a given coordinate
  ElementT* coordToPtr(const IndexT coord[D]) const{
    IndexT rv = 0;
    for(int i=0; i<D; ++i){
      #ifdef DEBUG
      JASSERT(0<=coord[i] && coord[i]<size(i))(coord[i])(size(i))
        .Text("Out of bounds access");
      #endif
      rv +=  this->multipliers()[i] * coord[i];
    }
    return this->base()+rv;
  }
  
  ///
  /// Fill _multipliers with a stock layout
  void setStockLayout(StockLayouts layout){
    IndexT mult = 1;
    if(layout == LAYOUT_ASCENDING){
      for(int i=0; i<D; ++i){
        this->multipliers()[i] = mult;
        mult *= size(i);
      }
    }else{
      for(int i=D-1; i>=0; --i){
        this->multipliers()[i] = mult;
        mult *= size(i);
      }
    }
  }
};

/**
 * We have divided MatrixRegion into many smaller classes (combined through a chain of inheritance)
 * so that small parts may easily be specialized.
 *
 * This part contains variable arg count methods.
 * GCC is bad at optimizing these, so we specialized these for commonly used types.
 */
template< typename TypeSpec >
class MatrixRegionVaArgsMethods : public MatrixRegionBasicMethods< TypeSpec > {
public:
  enum { D = TypeSpec::D };
  typedef typename TypeSpec::IndexT       IndexT;
  typedef typename TypeSpec::ElementT     ElementT;
  typedef typename TypeSpec::MatrixRegion MatrixRegion;
  typedef MatrixRegionBasicMethods<TypeSpec> Base;
  MatrixRegionVaArgsMethods( const typename TypeSpec::StorageT& s
                          , typename TypeSpec::ElementT* b
                          , const typename TypeSpec::IndexT* sizes
                          , const typename TypeSpec::IndexT* multipliers)
    : Base(s,b,sizes,multipliers)
  {}
  
  //these passthroughs must be declared here for overloading to work
  INLINE ElementT& cell(IndexT c[D]) const{ return this->Base::cell(c); }
  INLINE MatrixRegion region(const IndexT c1[D], const IndexT c2[D]) const{ return this->Base::region(c1,c2); }
  INLINE static MatrixRegion allocate(IndexT s[D]){ return Base::allocate(s); }
  
  ///
  /// Allocate a storage for a new MatrixRegion (va_args version)
  static MatrixRegion allocate(IndexT x, ...){
    IndexT c1[D];
    va_list ap;
    va_start(ap, x);
    c1[0]=x;
    for(int i=1; i<D; ++i) c1[i]=va_arg(ap, IndexT);
    va_end(ap);
    return allocate(c1);
  }

  ///
  /// Access a single cell of target matrix
  ElementT& cell(IndexT x, ...) const{
    IndexT c1[D];
    va_list ap;
    va_start(ap, x);
    c1[0]=x;
    for(int i=1; i<D; ++i) c1[i]=va_arg(ap, IndexT);
    va_end(ap);
    return cell(c1);
  }
  

  ///
  /// true if coord is in bounds
  bool contains(IndexT x, ...) const { 
    IndexT c1[D];
    va_list ap;
    va_start(ap, x);
    c1[0]=x;
    for(int i=1; i<D; ++i) c1[i]=va_arg(ap, IndexT);
    va_end(ap);
    return contains(c1);
  }

  ///
  /// Create a new iterator for a region of target matrix
  MatrixRegion region(IndexT x, ...) const{
    IndexT c1[D], c2[D];
    va_list ap;
    va_start(ap, x);
    c1[0]=x;
    for(int i=1; i<D; ++i) c1[i]=va_arg(ap, IndexT);
    for(int i=0; i<D; ++i) c2[i]=va_arg(ap, IndexT);
    va_end(ap);
    return region(c1,c2);
  }
  
};


/**
 * We have divided MatrixRegion into many smaller classes (combined through a chain of inheritance)
 * so that small parts may easily be specialized.
 *
 * This part contains the constructors, and is the final class called by the user.
 */
template< int D, typename ElementT>
class MatrixRegion : public MatrixRegionVaArgsMethods<MatrixRegionTypeSpec<D, ElementT> >{
public:
  typedef petabricks::MatrixRegionTypeSpec<D, ElementT> TypeSpec;
  typedef typename TypeSpec::IndexT IndexT;
  typedef typename TypeSpec::MutableMatrixRegion MutableMatrixRegion;
  typedef MatrixRegionVaArgsMethods<TypeSpec> Base;

  ///
  /// Constructor with a given layout
  MatrixRegion( const MatrixStoragePtr& s
              , ElementT* b
              , const IndexT sizes[D]
              , const IndexT multipliers[D])
    : Base(s, b, sizes, multipliers)
  {}

  ///
  /// Constructor with a stock layout
  MatrixRegion( const MatrixStoragePtr& s
              , ElementT* b
              , const IndexT sizes[D]
              , typename Base::StockLayouts layout = Base::LAYOUT_ASCENDING)
    : Base(s, b, sizes, NULL) 
  {
    this->setStockLayout(layout);
  }
  
  ///
  /// Copy constructor
  MatrixRegion( const MutableMatrixRegion& that )
    : Base(that.storage(), that.base(), that.sizes(), that.multipliers())
  {}

  ///
  /// Default constructor
  MatrixRegion() : Base(NULL, NULL, NULL, NULL) {}
};

} /* namespace petabricks*/

// specializations are a bit verbose, so we push them to their own file:
#include "matrixspecializations.h"

//some typedefs:
namespace petabricks {

typedef MatrixRegion<0,  MATRIX_ELEMENT_T> MatrixRegion0D;
typedef MatrixRegion<1,  MATRIX_ELEMENT_T> MatrixRegion1D;
typedef MatrixRegion<2,  MATRIX_ELEMENT_T> MatrixRegion2D;
typedef MatrixRegion<3,  MATRIX_ELEMENT_T> MatrixRegion3D;
typedef MatrixRegion<4,  MATRIX_ELEMENT_T> MatrixRegion4D;
typedef MatrixRegion<5,  MATRIX_ELEMENT_T> MatrixRegion5D;
typedef MatrixRegion<6,  MATRIX_ELEMENT_T> MatrixRegion6D;
typedef MatrixRegion<7,  MATRIX_ELEMENT_T> MatrixRegion7D;
typedef MatrixRegion<8,  MATRIX_ELEMENT_T> MatrixRegion8D;
typedef MatrixRegion<9,  MATRIX_ELEMENT_T> MatrixRegion9D;
typedef MatrixRegion<10, MATRIX_ELEMENT_T> MatrixRegion10D;
typedef MatrixRegion<11, MATRIX_ELEMENT_T> MatrixRegion11D;
typedef MatrixRegion<12, MATRIX_ELEMENT_T> MatrixRegion12D;
typedef MatrixRegion<13, MATRIX_ELEMENT_T> MatrixRegion13D;
typedef MatrixRegion<14, MATRIX_ELEMENT_T> MatrixRegion14D;
typedef MatrixRegion<15, MATRIX_ELEMENT_T> MatrixRegion15D;
typedef MatrixRegion<16, MATRIX_ELEMENT_T> MatrixRegion16D;
typedef MatrixRegion<17, MATRIX_ELEMENT_T> MatrixRegion17D;
typedef MatrixRegion<18, MATRIX_ELEMENT_T> MatrixRegion18D;
typedef MatrixRegion<19, MATRIX_ELEMENT_T> MatrixRegion19D;
typedef MatrixRegion<20, MATRIX_ELEMENT_T> MatrixRegion20D;
typedef MatrixRegion<21, MATRIX_ELEMENT_T> MatrixRegion21D;
typedef MatrixRegion<22, MATRIX_ELEMENT_T> MatrixRegion22D;
typedef MatrixRegion<23, MATRIX_ELEMENT_T> MatrixRegion23D;
typedef MatrixRegion<24, MATRIX_ELEMENT_T> MatrixRegion24D;
typedef MatrixRegion<25, MATRIX_ELEMENT_T> MatrixRegion25D;
typedef MatrixRegion<26, MATRIX_ELEMENT_T> MatrixRegion26D;
typedef MatrixRegion<27, MATRIX_ELEMENT_T> MatrixRegion27D;
typedef MatrixRegion<28, MATRIX_ELEMENT_T> MatrixRegion28D;
typedef MatrixRegion<29, MATRIX_ELEMENT_T> MatrixRegion29D;
typedef MatrixRegion<30, MATRIX_ELEMENT_T> MatrixRegion30D;
typedef MatrixRegion<31, MATRIX_ELEMENT_T> MatrixRegion31D;

typedef MatrixRegion<0,  const MATRIX_ELEMENT_T> ConstMatrixRegion0D;
typedef MatrixRegion<1,  const MATRIX_ELEMENT_T> ConstMatrixRegion1D;
typedef MatrixRegion<2,  const MATRIX_ELEMENT_T> ConstMatrixRegion2D;
typedef MatrixRegion<3,  const MATRIX_ELEMENT_T> ConstMatrixRegion3D;
typedef MatrixRegion<4,  const MATRIX_ELEMENT_T> ConstMatrixRegion4D;
typedef MatrixRegion<5,  const MATRIX_ELEMENT_T> ConstMatrixRegion5D;
typedef MatrixRegion<6,  const MATRIX_ELEMENT_T> ConstMatrixRegion6D;
typedef MatrixRegion<7,  const MATRIX_ELEMENT_T> ConstMatrixRegion7D;
typedef MatrixRegion<8,  const MATRIX_ELEMENT_T> ConstMatrixRegion8D;
typedef MatrixRegion<9,  const MATRIX_ELEMENT_T> ConstMatrixRegion9D;
typedef MatrixRegion<10, const MATRIX_ELEMENT_T> ConstMatrixRegion10D;
typedef MatrixRegion<11, const MATRIX_ELEMENT_T> ConstMatrixRegion11D;
typedef MatrixRegion<12, const MATRIX_ELEMENT_T> ConstMatrixRegion12D;
typedef MatrixRegion<13, const MATRIX_ELEMENT_T> ConstMatrixRegion13D;
typedef MatrixRegion<14, const MATRIX_ELEMENT_T> ConstMatrixRegion14D;
typedef MatrixRegion<15, const MATRIX_ELEMENT_T> ConstMatrixRegion15D;
typedef MatrixRegion<16, const MATRIX_ELEMENT_T> ConstMatrixRegion16D;
typedef MatrixRegion<17, const MATRIX_ELEMENT_T> ConstMatrixRegion17D;
typedef MatrixRegion<18, const MATRIX_ELEMENT_T> ConstMatrixRegion18D;
typedef MatrixRegion<19, const MATRIX_ELEMENT_T> ConstMatrixRegion19D;
typedef MatrixRegion<20, const MATRIX_ELEMENT_T> ConstMatrixRegion20D;
typedef MatrixRegion<21, const MATRIX_ELEMENT_T> ConstMatrixRegion21D;
typedef MatrixRegion<22, const MATRIX_ELEMENT_T> ConstMatrixRegion22D;
typedef MatrixRegion<23, const MATRIX_ELEMENT_T> ConstMatrixRegion23D;
typedef MatrixRegion<24, const MATRIX_ELEMENT_T> ConstMatrixRegion24D;
typedef MatrixRegion<25, const MATRIX_ELEMENT_T> ConstMatrixRegion25D;
typedef MatrixRegion<26, const MATRIX_ELEMENT_T> ConstMatrixRegion26D;
typedef MatrixRegion<27, const MATRIX_ELEMENT_T> ConstMatrixRegion27D;
typedef MatrixRegion<28, const MATRIX_ELEMENT_T> ConstMatrixRegion28D;
typedef MatrixRegion<29, const MATRIX_ELEMENT_T> ConstMatrixRegion29D;
typedef MatrixRegion<30, const MATRIX_ELEMENT_T> ConstMatrixRegion30D;
typedef MatrixRegion<31, const MATRIX_ELEMENT_T> ConstMatrixRegion31D;

typedef MATRIX_INDEX_T IndexT; 
typedef MATRIX_ELEMENT_T ElementT; 

} /* namespace petabricks*/

#endif
