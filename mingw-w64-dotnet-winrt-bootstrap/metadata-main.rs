use std::collections::BTreeSet;
use windows_metadata::reader::*;
use windows_metadata::{Type, TypeName, Value};
fn named(n: &TypeName, out: &mut BTreeSet<(String, String)>) {
    if n.namespace.starts_with("Windows.") {
        out.insert((n.namespace.clone(), n.name.clone()));
    }
    for t in &n.generics {
        ty(t, out);
    }
}
fn ty(t: &Type, out: &mut BTreeSet<(String, String)>) {
    match t {
        Type::ClassName(n) | Type::ValueName(n) => named(n, out),
        Type::Array(t)
        | Type::RefMut(t)
        | Type::RefConst(t)
        | Type::PtrMut(t, _)
        | Type::PtrConst(t, _)
        | Type::ArrayFixed(t, _) => ty(t, out),
        _ => {}
    }
}
fn attrs<'a>(item: impl HasAttributes<'a>, out: &mut BTreeSet<(String, String)>) {
    for a in item.attributes() {
        for (_, v) in a.value() {
            if let Value::TypeName(n) | Value::EnumValue(n, _) = v {
                named(&n, out);
            }
        }
    }
}
fn main() {
    windows_rdl::reader()
        .input("metadata/winrt")
        .output("Windows.winmd")
        .write()
        .expect("compile textual WinRT definitions");
    let file = File::read("Windows.winmd").expect("generated metadata");
    let index = Index::new(vec![file]);
    println!(
        "Generated {} WinRT types from textual RDL without binary metadata inputs",
        index.types().count()
    );
    let roots = [
        "Windows.Foundation",
        "Windows.Data.Xml.Dom",
        "Windows.UI.Notifications",
        "Windows.ApplicationModel.DataTransfer",
        "Windows.Graphics.Capture",
        "Windows.Graphics.Imaging",
        "Windows.Graphics.DirectX",
        "Windows.Media.Ocr",
        "Windows.Storage.Streams",
        "Windows.Globalization",
        "Windows.Management.Deployment.PackageManager",
        "Windows.UI.ViewManagement.UISettings",
        "Windows.Media.Core.MediaStreamSource",
        "Windows.Media.Core.MediaStreamSample",
        "Windows.Media.Core.VideoStreamDescriptor",
        "Windows.Media.Core.AudioStreamDescriptor",
        "Windows.Media.MediaProperties.MediaEncodingProfile",
        "Windows.Media.MediaProperties.MediaEncodingSubtypes",
        "Windows.Media.Transcoding.MediaTranscoder",
    ];
    let mut names = BTreeSet::new();
    for t in index.types() {
        if roots.iter().any(|r| {
            t.namespace().starts_with(r) || format!("{}.{}", t.namespace(), t.name()) == *r
        }) || t.namespace() == "Windows.ApplicationModel"
            && (t.name().starts_with("Package") || t.name().starts_with("IPackage"))
        {
            names.insert((t.namespace().to_string(), t.name().to_string()));
        }
    }
    let mut seen = BTreeSet::new();
    loop {
        let pending: Vec<_> = names.difference(&seen).cloned().collect();
        if pending.is_empty() {
            break;
        }
        for (ns, name) in pending {
            seen.insert((ns.clone(), name.clone()));
            let Some(t) = index.get(&ns, name.split('`').next().unwrap()).next() else {
                panic!("unresolved {ns}.{name}");
            };
            let generics: Vec<_> = t
                .generic_params()
                .map(|g| Type::Generic(g.name().to_string(), g.sequence()))
                .collect();
            if let Some(e) = t.extends() {
                ty(&e.ty(&generics), &mut names);
            }
            attrs(t, &mut names);
            for i in t.interface_impls() {
                ty(&i.interface(&generics), &mut names);
            }
            for f in t.fields() {
                ty(&f.ty(), &mut names);
            }
            for m in t.methods() {
                let s = m.signature(&generics);
                ty(&s.return_type, &mut names);
                for p in &s.types {
                    ty(p, &mut names);
                }
            }
        }
    }
    let args = names
        .iter()
        .map(|(ns, n)| format!("{ns}.{n}"))
        .collect::<Vec<_>>()
        .join("\n");
    let included: Vec<_> = names.iter().map(|(ns, n)| format!("{ns}.{n}")).collect();
    let excluded = index
        .types()
        .filter_map(|t| {
            let key = (t.namespace().to_string(), t.name().to_string());
            let full = format!("{}.{}", t.namespace(), t.name());
            (!names.contains(&key) && included.iter().any(|n| full.starts_with(n))).then_some(full)
        })
        .collect::<Vec<_>>()
        .join("\n");
    std::fs::write(
        "projection-types.rsp",
        format!("-include\n{args}\n-exclude\n{excluded}\n"),
    )
    .unwrap();
    println!(
        "Selected {} types including transitive dependencies",
        names.len()
    );
}
