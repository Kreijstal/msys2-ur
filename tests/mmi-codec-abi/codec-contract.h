/* Compile the pinned Microsoft codec declarations with the Windows MI ABI. */
#include <sal.h>
#include <mi.h>
/* Select the header's Windows packing/SAL path; no implementation is replaced. */
#ifndef _MSC_VER
#define _MSC_VER 1930
#define MMI_AUDIT_DEFINED_MSC_VER
#endif
#include "micodec.h"
#ifdef MMI_AUDIT_DEFINED_MSC_VER
#undef _MSC_VER
#undef MMI_AUDIT_DEFINED_MSC_VER
#endif
