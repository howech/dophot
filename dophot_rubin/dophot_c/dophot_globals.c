/*
 * dophot_globals.c
 * Single definition point for all DoPHOT global variables
 * This file is compiled once and linked first to ensure proper initialization
 *
 * By defining DOPHOT_DEFINE_GLOBALS before including struct headers,
 * this file contains the actual definitions (not extern declarations)
 */

#define DOPHOT_DEFINE_GLOBALS

#include "structs/tuneable.h"
#include "structs/addobj_struct.h"
#include "structs/aperlist_struct.h"
#include "structs/byvirtue_struct.h"
#include "structs/changed_struct.h"
#include "structs/clobber_struct.h"
#include "structs/crudestat_struct.h"
#include "structs/ctimes_struct.h"
#include "structs/dfake_struct.h"
#include "structs/drfake_struct.h"
#include "structs/efake_struct.h"
#include "structs/empmom_struct.h"
#include "structs/eoff_struct.h"
#include "structs/estuff_struct.h"
#include "structs/fitarrays_struct.h"
#include "structs/fitting_matrices_struct.h"
#include "structs/fixpass_struct.h"
#include "structs/free_parking_struct.h"
#include "structs/funnypass_struct.h"
#include "structs/galpass_struct.h"
#include "structs/hubvar_struct.h"
#include "structs/imdev_struct.h"
#include "structs/median_struct.h"
#include "structs/model_struct.h"
#include "structs/odfake_struct.h"
#include "structs/oefake_struct.h"
#include "structs/oimdev_struct.h"
#include "structs/opqfake_struct.h"
#include "structs/orsfake_struct.h"
#include "structs/parinterp_struct.h"
#include "structs/parpred_struct.h"
#include "structs/passimp_struct.h"
#include "structs/passmask_struct.h"
#include "structs/passweird_struct.h"
#include "structs/pqfake_struct.h"
#include "structs/probpass_struct.h"
#include "structs/rsfake_struct.h"
#include "structs/search_struct.h"
#include "structs/skyvar_struct.h"
#include "structs/starlist_struct.h"
#include "structs/subraster_struct.h"
#include "structs/trans7_struct.h"
#include "structs/undergnd_struct.h"
#include "structs/unitize_struct.h"
#include "headers/logh.h"
