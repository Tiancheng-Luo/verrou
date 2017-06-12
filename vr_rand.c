/*--------------------------------------------------------------------*/
/*--- Verrou: a FPU instrumentation tool.                          ---*/
/*--- Interface for random number generation.                      ---*/
/*---                                                    vr_rand.c ---*/
/*--------------------------------------------------------------------*/

/*
   This file is part of Verrou, a FPU instrumentation tool.

   Copyright (C) 2014-2016
     F. Févotte     <francois.fevotte@edf.fr>
     B. Lathuilière <bruno.lathuiliere@edf.fr>

   This program is free software; you can redistribute it and/or
   modify it under the terms of the GNU General Public License as
   published by the Free Software Foundation; either version 2 of the
   License, or (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
   02111-1307, USA.

   The GNU General Public License is contained in the file COPYING.
*/

#include "vr_rand.h"
#include "pub_tool_libcproc.h"
#include "pub_tool_libcprint.h"

Vr_Rand vr_rand;

static int vr_rand_next (Vr_Rand * r){
  r->next_ = r->next_ * 1103515245 + 12345;
  return (unsigned int)(r->next_/65536) % 32768;
}

int vr_rand_max () {
  return 32767;
}

void vr_rand_setSeed (Vr_Rand * r, unsigned int c) {
  r->reload_  = 31;
  r->count_   = 0;
  r->seed_    = c;
  r->next_    = c;
  r->current_ = vr_rand_next (r);
}

void vr_rand_autoSeed (Vr_Rand * r) {
  struct vki_timeval now;
  VG_(gettimeofday)(&now, NULL);
  unsigned int pid = VG_(getpid)();
  unsigned int seed = now.tv_usec + pid;
  vr_rand_setSeed (r, seed);
  VG_(umsg)("First seed : %u\n", vr_rand_getSeed(r));
}

unsigned int vr_rand_getSeed (Vr_Rand * r) {
  return r->seed_;
}

Bool vr_rand_bool (Vr_Rand * r) {
  if (r->count_ == r->reload_){
    r->current_ = vr_rand_next (r);
    r->count_ = 0;
  }
  Bool res = (r->current_ >> (r->count_++)) & 1;
  // VG_(umsg)("Count : %u  res: %u\n", r->count_ ,res);
  return res;
}

int vr_rand_int (Vr_Rand * r) {
  return vr_rand_next (r);
}
