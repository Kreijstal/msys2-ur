$ErrorActionPreference = 'Stop'
# Run with Windows PowerShell for the built-in MMI baseline. The source port
# uses its own separately built .NET 8 consumer and never loads this assembly.
foreach ($flag in @([Microsoft.Management.Infrastructure.CimFlags]::Borrow, [Microsoft.Management.Infrastructure.CimFlags]::Adopt)) {
    $owner = [Microsoft.Management.Infrastructure.CimInstance]::new('MSYS2_MemoryFlagBaseline')
    try {
        $property = [Microsoft.Management.Infrastructure.CimProperty]::Create('Label', 'seed', [Microsoft.Management.Infrastructure.CimType]::String, $flag)
        $owner.CimInstanceProperties.Add($property)
        $stored = $owner.CimInstanceProperties['Label']
        if ($stored.Value -cne 'seed') { throw 'Baseline property value lost' }
        if (($stored.Flags -band ([Microsoft.Management.Infrastructure.CimFlags]::Borrow -bor [Microsoft.Management.Infrastructure.CimFlags]::Adopt)) -ne 0) { throw 'Baseline unexpectedly retained a native memory-transfer flag' }
        [pscustomobject]@{
            Requested = $flag.ToString()
            StandaloneFlags = $property.Flags.ToString()
            StoredFlags = $stored.Flags.ToString()
            Value = $stored.Value
            Assembly = [Microsoft.Management.Infrastructure.CimInstance].Assembly.FullName
            Location = [Microsoft.Management.Infrastructure.CimInstance].Assembly.Location
        } | ConvertTo-Json -Compress
    }
    finally { $owner.Dispose() }
}
