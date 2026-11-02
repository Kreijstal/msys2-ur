"""Replay pinned compiler policy property elements, preserving their conditions."""
import copy
import hashlib
import xml.etree.ElementTree as E

def write_policy(source, path):
    settings = E.parse(source / 'eng/targets/Settings.props')
    imports = E.parse(source / 'eng/targets/Imports.targets')
    root = E.Element('Project')
    group = E.SubElement(root, 'PropertyGroup')
    for name in ['Features', 'Nullable']:
        group.append(copy.deepcopy(settings.find('./PropertyGroup/' + name)))
    # Original source targets C# and multi-targets Core plus NS2. The selection
    # below is the unchanged C# branch of Settings.props, excluding unrelated VB.
    branch = settings.find("./Choose/When[@Condition=\"'$(Language)' == 'C#'\"]/PropertyGroup")
    assert branch is not None
    root.append(copy.deepcopy(branch))
    group = E.SubElement(root, 'PropertyGroup')
    prop = imports.find('./PropertyGroup/DisableNullableWarnings')
    assert prop is not None
    group.append(copy.deepcopy(prop))
    nullable_group = next(g for g in imports.findall('./PropertyGroup') if g.get('Condition') == "'$(DisableNullableWarnings)' == 'true'")
    root.append(copy.deepcopy(nullable_group))
    E.indent(root)
    E.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
    return {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [source / 'eng/targets/Settings.props', source / 'eng/targets/Imports.targets']}
