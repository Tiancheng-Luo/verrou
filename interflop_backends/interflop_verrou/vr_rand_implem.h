/*--------------------------------------------------------------------*/
/*--- Verrou: a FPU instrumentation tool.                          ---*/
/*--- Interface for random number generation.                      ---*/
/*---                                             vr_rand_implem.h ---*/
/*--------------------------------------------------------------------*/

/*
   This file is part of Verrou, a FPU instrumentation tool.

   Copyright (C) 2014-2021 EDF
     F. Févotte     <francois.fevotte@edf.fr>
     B. Lathuilière <bruno.lathuiliere@edf.fr>

   This program is free software; you can redistribute it and/or
   modify it under the terms of the GNU Lesser General Public License as
   published by the Free Software Foundation; either version 2.1 of the
   License, or (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU Lesser General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
   02111-1307, USA.

   The GNU Lesser General Public License is contained in the file COPYING.
*/


//#include "vr_rand.h"

//Warning FILE include in vr_rand.h

#include "vr_op.hxx"

#ifdef INTERNAL_BACKEND_DEBUG
#include <iostream>
#endif


#ifdef VERROU_LOWGEN
inline static uint64_t vr_rand_next (Vr_Rand * r){
r->next_ = r->next_ * 1103515245 + 12345;
  return (uint64_t)((r->next_/65536) % 32768);
}
inline uint64_t vr_rand_max () {
  return 32767;// 2**15= 32768
}


inline uint32_t vr_loop(){
  return 14;
}

#else
inline static uint64_t vr_rand_next (Vr_Rand * r){
  return tinymt64_generate_uint64(&(r->gen_) );
}
inline uint64_t vr_rand_max () {
  uint64_t max=2147483647;
  return max;
}

inline uint32_t vr_loop(){
return 63;
}
#endif

inline void vr_rand_setSeed (Vr_Rand * r, uint64_t c) {
  r->count_   = 0;
  r->seed_    = c;
#ifdef VERROU_LOWGEN
  r->next_    = c;
#else
  tinymt64_init(&(r->gen_),c);
#endif

  r->seedParam[0]=vr_rand_next (r) |1; //b
  r->seedParam[1]=vr_rand_next (r) |1; //a1
  r->seedParam[2]=vr_rand_next (r) |1; //a2
  r->seedParam[3]=vr_rand_next (r) |1; //a3
#ifdef INTERNAL_BACKEND_DEBUG
  std::cout << "b:" <<  r->seedParam[0]<<std::endl;
  std::cout << "a1:" <<  r->seedParam[1]<<std::endl;
  std::cout << "a2:" <<  r->seedParam[2]<<std::endl;
  std::cout << "a3:" <<  r->seedParam[3]<<std::endl;
#endif
  r->current_ = vr_rand_next (r);
}





inline uint64_t vr_rand_getSeed (const Vr_Rand * r) {
return r->seed_;
}

inline bool vr_rand_bool (Vr_Rand * r) {
if (r->count_ == vr_loop()){
    r->current_ = vr_rand_next (r);
    r->count_ = 0;
  }
  bool res = (r->current_ >> (r->count_++)) & 1;
  // VG_(umsg)("Count : %u  res: %u\n", r->count_ ,res);
  return res;
}

inline uint32_t vr_rand_int (Vr_Rand * r) {
  uint64_t res=vr_rand_next (r) ;//% vr_rand_max();
  return (uint32_t)res;//vr_rand_next (r);
}

inline double  vr_rand_double (Vr_Rand * r) {
#ifdef VERROU_LOWGEN
  return (double) vr_rand_next (r) / (double)vr_rand_max() ;//% vr_rand_max();
#else
  return tinymt64_generate_doubleOO(&(r->gen_) );
#endif
}



/*
 * produces a pseudo random number in a deterministic way
 * the same seed and inputs will always produce the same output
 */
template<class OP>
inline bool vr_rand_bool_det (const Vr_Rand * r, const typename OP::PackArgs& p) {
#ifdef VERROU_LOWGEN
  // returns a one bit hash as a PRNG
  // uses Dietzfelbinger's multiply shift hash function
  // see `High Speed Hashing for Integers and Strings` (https://arxiv.org/abs/1504.06804)
  //  const uint64_t oddSeed = seed | 1; // insures seed is odd

  const uint64_t argsHash =  p.getMultiply(r, (OP*)NULL);
#else
  const uint64_t argsHash =  p.getPreciseHash(r, (OP*)NULL);
#endif

  const bool res = (argsHash) >> 63;
#ifdef INTERNAL_BACKEND_DEBUG
 std::cout << "arg1: "<<  p.arg1 << " arg2: "<< p.arg2 << " argsHash : "<< argsHash << " res : " <<res <<std::endl;
#endif

  return res;
}

/* inline uint64_t vr_rand_max_det () { */
/*   uint64_t max= 4294967295; //2**32-1 */
/*   return max; */
/* } */


template<class OP>
inline double vr_rand_double_det (const Vr_Rand * r, const typename OP::PackArgs& p) {
#ifdef VERROU_LOWGEN
  const uint64_t argsHash =   p.getMultiply(r,(OP*)NULL);
  const uint32_t res = (argsHash) >> 32;
  uint64_t max= 4294967295; //2**32-1
  double ratio ((double)res / (double) max);

  #else
  const uint64_t argsHash =  p.getPreciseHash(r, (OP*)NULL);
  double ratio= (double )argsHash  / (double) (0xFFFFFFFFFFFFFFFF);
#endif

  //const uint64_t seed = OP::getHash() ^ vr_rand_getSeed(r);


  // returns a one bit hash as a PRNG
  // uses Dietzfelbinger's multiply shift hash function
  // see `High Speed Hashing for Integers and Strings` (https://arxiv.org/abs/1504.06804)
//const uint64_t oddSeed = seed | 1; // insures seed is odd


#ifdef INTERNAL_BACKEND_DEBUG
 std::cout << "arg1: "<<  p.arg1 << " arg2: "<< p.arg2 << " argsHash : "<< argsHash << " resRatio: "  << ratio <<std::endl;
#endif
 return ratio;
}
