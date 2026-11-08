/*
**==============================================================================
**
** Copyright (c) Microsoft Corporation. All rights reserved. See file LICENSE
** for license information.
**
**==============================================================================
*/


using Microsoft.Management.Infrastructure.Generic;
using Microsoft.Management.Infrastructure.Native;
using Microsoft.Management.Infrastructure.Options.Internal;
using System;
using System.Collections.Generic;

namespace Microsoft.Management.Infrastructure.Internal.Data
{
    internal class CimPropertiesCollection : CimKeyedCollection<CimProperty>
    {
        private readonly CimInstance _instance;

        internal CimPropertiesCollection(CimInstance instance)
        {
            this._instance = instance;
        }

        public override void Add(CimProperty newProperty)
        {
            if (newProperty == null)
            {
                throw new ArgumentNullException("newProperty");
            }

            object managedValue = newProperty.Value;
            using var native = ValueHelpers.ConvertToNativeLayer(managedValue, newProperty.CimType);
            try
            {
                MI_Result result = this._instance.InstanceHandle.AddElement(newProperty.Name,
                    native, newProperty.CimType.FromCimType(),
                    newProperty.Flags.FromCimFlags() & ~(MI_Flags.MI_FLAG_BORROW | MI_Flags.MI_FLAG_ADOPT));
                CimException.ThrowIfMiResultFailure(result);
            }
            finally
            {
                GC.KeepAlive(managedValue);
                GC.KeepAlive(newProperty);
                GC.KeepAlive(_instance);
            }
        }

        public override int Count
        {
            get
            {
                // The native function receives only a raw pointer. An optimized
                // caller may otherwise finalize a transient instance mid-call.
                try
                {
                    uint count;
                    MI_Result result = this._instance.InstanceHandle.GetElementCount(out count);
                    CimException.ThrowIfMiResultFailure(result);
                    return (int)count;
                }
                finally { GC.KeepAlive(this._instance); }
            }
        }

        public override CimProperty this[string propertyName]
        {
            get
            {
                if (string.IsNullOrWhiteSpace(propertyName))
                {
                    throw new ArgumentNullException("propertyName");
                }

                MI_Value value;
                MI_Type type;
                MI_Flags flags;
                UInt32 index;
                MI_Result result = this._instance.InstanceHandle.GetElement(propertyName,
                                      out value,
                                      out type,
                                      out flags,
                                      out index);
                using (value)
                switch (result)
                {
                    case MI_Result.MI_RESULT_NO_SUCH_PROPERTY:
                        return null;

                    default:
                        CimException.ThrowIfMiResultFailure(result);
                        return new CimPropertyOfInstance(this._instance, (int)index);
                }
            }
        }

        public override IEnumerator<CimProperty> GetEnumerator()
        {
            int count = this.Count;
            for (int i = 0; i < count; i++)
            {
                yield return new CimPropertyOfInstance(this._instance, i);
            }
        }
    }
}
