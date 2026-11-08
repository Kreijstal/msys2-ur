/*
**==============================================================================
**
** Copyright (c) Microsoft Corporation. All rights reserved. See file LICENSE
** for license information.
**
**==============================================================================
*/


using System;
using Microsoft.Management.Infrastructure.Native;
using System.Globalization;
using System.Runtime.InteropServices;

namespace Microsoft.Management.Infrastructure.Internal
{
    internal static class ValueHelpers
    {
        internal static void ThrowIfMismatchedType(MI_Type type, object managedValue)
        {
            if (managedValue is MI_Value value && value.Type.HasValue && value.Type.Value != type)
                throw new InvalidCastException("The value does not match the requested CIM type.");
        }

        internal static MI_Value ConvertToNativeLayer(object value, CimType cimType)
        {
            var cimInstance = value as CimInstance;
            if (cimInstance != null)
            {
                MI_Value retval = new MI_Value();
                if (cimType == CimType.Reference) retval.Reference = cimInstance.InstanceHandle;
                else retval.Instance = cimInstance.InstanceHandle;
                return retval;
            }

            var arrayOfCimInstances = value as CimInstance[];
            if (arrayOfCimInstances != null)
            {
                MI_Instance[] arrayOfInstanceHandles = new MI_Instance[arrayOfCimInstances.Length];
                for (int i = 0; i < arrayOfCimInstances.Length; i++)
                {
                    CimInstance inst = arrayOfCimInstances[i];
                    if (inst == null)
                    {
                        arrayOfInstanceHandles[i] = null;
                    }
                    else
                    {
                        arrayOfInstanceHandles[i] = inst.InstanceHandle;
                    }
                }

                MI_Value retval = new MI_Value();
                if (cimType == CimType.ReferenceArray) retval.ReferenceA = arrayOfInstanceHandles;
                else retval.InstanceA = arrayOfInstanceHandles;
                return retval;
            }

            // TODO: What to do with Unknown types? Ignore? Uncomment and remove return line immediately below.
            return CimProperty.ConvertToNativeLayer(value, cimType);
            /*
            if (cimType != CimType.Unknown)
            {
            return CimProperty.ConvertToNativeLayer(value, cimType);
            }
            else
            {
            return value;
            }
            */
        }

        internal static MI_Value ConvertToNativeLayer(object value)
        {
            return ConvertToNativeLayer(value, CimType.Unknown);
        }

        internal static object ConvertFromNativeLayer(
            MI_Value value,
            MI_Type type,
            MI_Flags flags,
            CimInstance parent = null,
            bool clone = false)
        {
            try
            {
                if ((flags & MI_Flags.MI_FLAG_NULL) == MI_Flags.MI_FLAG_NULL)
                {
                    return null;
                }

                // Windows MI uses { data = NULL, size = 0 } for an empty,
                // non-NULL array. MI_FLAG_NULL above separately identifies NULL.
                if ((type & MI_TypeFlags.MI_ARRAY) != 0 &&
                    Marshal.ReadIntPtr(value.Ptr) == IntPtr.Zero && Marshal.ReadInt32(value.Ptr, IntPtr.Size) == 0)
                {
                    switch (type)
                    {
                        case MI_Type.MI_BOOLEANA: return Array.Empty<bool>();
                        case MI_Type.MI_UINT8A: return Array.Empty<byte>();
                        case MI_Type.MI_SINT8A: return Array.Empty<sbyte>();
                        case MI_Type.MI_UINT16A: return Array.Empty<ushort>();
                        case MI_Type.MI_SINT16A: return Array.Empty<short>();
                        case MI_Type.MI_UINT32A: return Array.Empty<uint>();
                        case MI_Type.MI_SINT32A: return Array.Empty<int>();
                        case MI_Type.MI_UINT64A: return Array.Empty<ulong>();
                        case MI_Type.MI_SINT64A: return Array.Empty<long>();
                        case MI_Type.MI_REAL32A: return Array.Empty<float>();
                        case MI_Type.MI_REAL64A: return Array.Empty<double>();
                        case MI_Type.MI_CHAR16A: return Array.Empty<char>();
                        case MI_Type.MI_DATETIMEA: return Array.Empty<object>();
                        case MI_Type.MI_STRINGA: return Array.Empty<string>();
                        case MI_Type.MI_REFERENCEA: return Array.Empty<CimInstance>();
                        case MI_Type.MI_INSTANCEA: return Array.Empty<CimInstance>();
                    }
                }

                if (type == MI_Type.MI_INSTANCE || type == MI_Type.MI_REFERENCE)
                {
                    MI_Instance nativeInstance = type == MI_Type.MI_REFERENCE ? value.Reference : value.Instance;
                    try
                    {
                        if (nativeInstance == null || nativeInstance.IsNull) return null;
                        CimInstance instance = new CimInstance(clone ? nativeInstance.Clone() : nativeInstance);
                        if (parent != null)
                        {
                            instance.SetCimSessionComputerName(parent.GetCimSessionComputerName());
                            instance.SetCimSessionInstanceId(parent.GetCimSessionInstanceId());
                        }
                        return instance;
                    }
                    finally { if (clone) nativeInstance?.Dispose(); }
                }
                else if (type == MI_Type.MI_INSTANCEA || type == MI_Type.MI_REFERENCEA)
                {
                    MI_Instance[] nativeInstances = type == MI_Type.MI_REFERENCEA ? value.ReferenceA : value.InstanceA;
                    if (nativeInstances == null) return null;
                    CimInstance[] instances = new CimInstance[nativeInstances.Length];
                    try
                    {
                        for (int i = 0; i < nativeInstances.Length; i++)
                        {
                            MI_Instance handle = nativeInstances[i];
                            if (handle == null || handle.IsNull) continue;
                            instances[i] = new CimInstance(clone ? handle.Clone() : handle);
                            if (parent != null)
                            {
                                instances[i].SetCimSessionComputerName(parent.GetCimSessionComputerName());
                                instances[i].SetCimSessionInstanceId(parent.GetCimSessionInstanceId());
                            }
                        }
                        return instances;
                    }
                    catch
                    {
                        if (clone) foreach (CimInstance instance in instances) instance?.Dispose();
                        throw;
                    }
                    finally { if (clone) foreach (MI_Instance handle in nativeInstances) handle?.Dispose(); }
                }
                else if (type == MI_Type.MI_DATETIME)
                {
                    return value.Datetime.ConvertFromNativeLayer();
                }
                else if (type == MI_Type.MI_DATETIMEA)
                {
                    MI_Datetime[] nativeDatetimes = value.DatetimeA;
                    if (nativeDatetimes == null) return null;
                    int length = nativeDatetimes.Length;
                    object[] arrayOfDatetimes = new object[length];
                    for (int i = 0; i < length; i++)
                    {
                        arrayOfDatetimes[i] = nativeDatetimes[i].ConvertFromNativeLayer();
                    }
                    return arrayOfDatetimes;
                }
                else
                {
                    return value.GetValue(type);
                }
            }
            finally { GC.KeepAlive(value); }
        }
    }
}
