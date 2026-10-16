# shellcheck shell=bash
#
# javabuild.sh - build Java libraries from source without Maven or Ant.
#
# Sourced by the PKGBUILDs of the source-bootstrapped Java/Maven packages:
#
#   source "${MINGW_PREFIX}/share/java-build-helper/javabuild.sh"
#
# Like GNU Guix's ant-build-system it compiles each module with javac and
# packs it with jar; generated metadata that a Maven build would add
# (plugin.xml, Plexus components.xml, the Sisu index) is produced by
# annotation processors shipped with this helper or by Sisu itself.
#
# Every artifact is staged in a build-local Maven repository ($JB_STAGE) and
# installed into the system Maven repository
#   ${MINGW_PREFIX}/share/maven-repo/<group path>/<artifactId>/<version>/
# with a flattened POM: no parent, no dependencyManagement, and only the
# compile/runtime dependencies, each pinned to the version that is packaged.
# The jar is also hard-linked as ${MINGW_PREFIX}/share/java/<artifactId>.jar.
#
# Dependency specs used below:  groupId:artifactId[#classifier][/scope][?][!g:a...]
#   /scope  compile (default), runtime, provided, test
#   ?       optional
#   !g:a    exclusion (repeatable), written to the POM and honoured by jb_closure
#   =ver    pin a version that is not installed (rarely needed)

JB_HOME="${MINGW_PREFIX}/share/java-build-helper"
JB_SYSREPO="${MINGW_PREFIX}/share/maven-repo"
JB_STAGE="${srcdir:-$PWD}/jb-repo"
: "${JB_RELEASE:=8}"
# JB_TARGET=8 compiles with -source 8 -target 8 against the running JDK's API
# instead of --release (what Maven's source/target settings do upstream)
: "${JB_TARGET:=}"
: "${JB_ENCODING:=UTF-8}"

_jb_die() {
  echo "javabuild: $*" >&2
  return 1
}

# Windows form of one or more paths (the JDK is a native Windows program)
jb_w() {
  cygpath -m "$@"
}

# parse a spec into the globals _g _a _c _s _o _v
_jb_spec() {
  local s=$1
  _v= _o= _s=compile _c= _x=
  # exclusions: g:a...!xg:xa!yg:ya
  [[ $s == *'!'* ]] && { _x=${s#*!}; _x=${_x//!/ }; s=${s%%!*}; }
  [[ $s == *'?' ]] && { _o=1; s=${s%'?'}; }
  [[ $s == *=* ]] && { _v=${s#*=}; s=${s%%=*}; }
  [[ $s == */* ]] && { _s=${s#*/}; s=${s%%/*}; }
  [[ $s == *'#'* ]] && { _c=${s#*#}; s=${s%%#*}; }
  [[ $s == ?*:?* && $s != *:*:* ]] || _jb_die "bad dependency spec '$1'" || return 1
  _g=${s%%:*}
  _a=${s#*:}
}

# directory and version of an installed or staged artifact: sets _dir _ver
_jb_locate() {
  local g=$1 a=$2 base d v
  local -a found
  for base in "$JB_STAGE" "$JB_SYSREPO"; do
    d="$base/${g//.//}/$a"
    [[ -d $d ]] || continue
    found=()
    for v in "$d"/*/; do
      v=${v%/}
      v=${v##*/}
      [[ -f $d/$v/$a-$v.pom ]] && found+=("$v")
    done
    if (( ${#found[@]} == 1 )); then
      _dir="$d/${found[0]}"
      _ver=${found[0]}
      return 0
    elif (( ${#found[@]} > 1 )); then
      _jb_die "several versions of $g:$a in $base: ${found[*]}"
      return 1
    fi
  done
  _jb_die "$g:$a is neither staged nor installed (missing dependency?)"
}

# version of an artifact: jb_version groupId:artifactId
jb_version() {
  _jb_spec "$1" || return 1
  _jb_locate "$_g" "$_a" || return 1
  echo "$_ver"
}

# jar file of an artifact: jb_jarpath groupId:artifactId[#classifier]
jb_jarpath() {
  _jb_spec "$1" || return 1
  _jb_locate "$_g" "$_a" || return 1
  local f="$_dir/$_a-$_ver${_c:+-$_c}.jar"
  [[ -f $f ]] || _jb_die "no jar $f" || return 1
  echo "$f"
}

# print "g:a[#c]" for every compile/runtime, non-optional dependency of a POM
_jb_pomdeps() {
  awk '
    /<dependency>/ { g=""; a=""; c=""; s="compile"; o=""; x=""; inside=1; next }
    inside && /<exclusion>/  { inex=1; next }
    inex && /<groupId>/      { gsub(/.*<groupId>|<\/groupId>.*/, ""); xg=$0; next }
    inex && /<artifactId>/   { gsub(/.*<artifactId>|<\/artifactId>.*/, ""); x=x "!" xg ":" $0; next }
    /<\/exclusion>/          { inex=0; next }
    inside && /<groupId>/    { gsub(/.*<groupId>|<\/groupId>.*/, ""); g=$0 }
    inside && /<artifactId>/ { gsub(/.*<artifactId>|<\/artifactId>.*/, ""); a=$0 }
    inside && /<classifier>/ { gsub(/.*<classifier>|<\/classifier>.*/, ""); c=$0 }
    inside && /<scope>/      { gsub(/.*<scope>|<\/scope>.*/, ""); s=$0 }
    inside && /<optional>/   { gsub(/.*<optional>|<\/optional>.*/, ""); o=$0 }
    /<\/dependency>/ {
      inside=0
      if ((s == "compile" || s == "runtime") && o != "true")
        print g ":" a (c != "" ? "#" c : "") x
    }' "$1"
}

# transitive closure of specs (direct ones always included): one g:a[#c] per
# line; exclusions apply to the subtree of the dependency that declares them
jb_closure() {
  local -A seen=()
  local -a queue=() out=()
  local s key item ex x
  for s in "$@"; do
    _jb_spec "$s" || return 1
    queue+=("$_g:$_a${_c:+#$_c}|${_x}")
  done
  while (( ${#queue[@]} )); do
    item=${queue[0]}
    queue=("${queue[@]:1}")
    key=${item%%|*}
    ex=${item#*|}
    [[ -n ${seen[$key]:-} ]] && continue
    seen[$key]=1
    out+=("$key")
    _jb_spec "$key" || return 1
    _jb_locate "$_g" "$_a" || return 1
    while read -r s; do
      [[ -n $s ]] || continue
      _jb_spec "$s" || return 1
      local dk="$_g:$_a${_c:+#$_c}"
      [[ -n ${seen[$dk]:-} ]] && continue
      [[ " $ex " == *" $_g:$_a "* || " $ex " == *" $_g:* "* ]] && continue
      queue+=("$dk|${ex:+$ex }${_x}")
    done < <(_jb_pomdeps "$_dir/$_a-$_ver.pom")
  done
  printf '%s\n' "${out[@]}"
}

# classpath (Windows form, ';'-separated) of specs and their dependencies
#   jb_cp spec... [-- extra paths...]
jb_cp() {
  local -a specs=() extra=() parts=()
  while (( $# )); do
    if [[ $1 == -- ]]; then shift; extra=("$@"); break; fi
    specs+=("$1"); shift
  done
  local s j closure
  if (( ${#specs[@]} )); then
    closure=$(jb_closure "${specs[@]}") || return 1
    while read -r s; do
      [[ -n $s ]] || continue
      _jb_spec "$s" || return 1
      _jb_locate "$_g" "$_a" || return 1
      j="$_dir/$_a-$_ver${_c:+-$_c}.jar"
      [[ -f $j ]] || continue        # pom-only artifacts
      parts+=("$(jb_w "$j")")
    done <<< "$closure"
  fi
  for s in "${extra[@]}"; do
    parts+=("$(jb_w "$s")")
  done
  local IFS=';'
  echo "${parts[*]}"
}

# compile:  jb_javac [javac options...] -- sources-or-directories...
#   JB_RELEASE (default 8) or JB_TARGET, and JB_ENCODING apply; module-info.java and
#   package-info.java without a package are skipped unless JB_MODULE_INFO=1.
#   JB_SRC_EXCLUDE: extended regex of source paths to leave out.
jb_javac() {
  local -a opts=() srcs=()
  while (( $# )); do
    if [[ $1 == -- ]]; then shift; srcs=("$@"); break; fi
    opts+=("$1"); shift
  done
  local list
  list=$(mktemp "${srcdir:-/tmp}/jb-sources.XXXXXX")
  local s
  for s in "${srcs[@]}"; do
    if [[ -d $s ]]; then
      find "$s" -name '*.java' | sort
    else
      echo "$s"
    fi
  done | { if [[ ${JB_MODULE_INFO:-0} == 1 ]]; then cat; else grep -v '/module-info\.java$'; fi; } \
       | { if [[ -n ${JB_SRC_EXCLUDE:-} ]]; then grep -Ev "$JB_SRC_EXCLUDE"; else cat; fi; } \
       | while read -r s; do jb_w "$s"; done | sed 's/.*/"&"/' > "$list"
  if [[ ! -s $list ]]; then
    rm -f "$list"
    _jb_die "jb_javac: no Java sources in ${srcs[*]}"
    return 1
  fi
  local -a rel=()
  if [[ -n $JB_TARGET ]]; then
    rel=(-source "$JB_TARGET" -target "$JB_TARGET")
  elif [[ -n $JB_RELEASE ]]; then
    rel=(--release "$JB_RELEASE")
  fi
  local n
  n=$(wc -l < "$list")
  echo "javabuild: javac ($n files) ${opts[*]}" | cut -c1-300
  # -Xpkginfo:always: package-info.class for every package-info.java, as
  # maven-compiler-plugin's createMissingPackageInfoClass does
  javac "${rel[@]}" -encoding "$JB_ENCODING" -nowarn -Xlint:-options -Xpkginfo:always \
    -XDsuppressNotes -Xmaxerrs 200 "${opts[@]}" "@$(jb_w "$list")"
  local rc=$?
  rm -f "$list"
  return $rc
}

# javac options that run annotation processors; echo one option per line
#   jb_processor_opts [mojo=<plugin.properties>] [plexus] [sisu]
# use:  mapfile -t popts < <(jb_processor_opts sisu plexus)
jb_processor_opts() {
  local -a procs=() path=("$(jb_w "$JB_HOME/javabuild.jar")") opts=()
  local p
  for p in "$@"; do
    case $p in
      mojo=*)
        procs+=(jb.MojoDescriptorProcessor)
        opts+=("-Ajb.plugin=$(jb_w "${p#mojo=}")") ;;
      plexus)
        procs+=(jb.PlexusComponentsProcessor) ;;
      sisu)
        procs+=(org.eclipse.sisu.space.SisuIndexAPT6)
        path+=("$(jb_w "$(jb_jarpath org.eclipse.sisu:org.eclipse.sisu.inject)")")
        path+=("$(jb_w "$(jb_jarpath javax.inject:javax.inject)")") ;;
      *) _jb_die "unknown processor '$p'"; return 1 ;;
    esac
  done
  local IFS=,
  printf '%s\n' -processor "${procs[*]}"
  IFS=';'
  printf '%s\n' -processorpath "${path[*]}" "${opts[@]}"
}

# copy resource directories into the class output directory
#   jb_resources <classes-dir> <resource-dir>...
jb_resources() {
  local out=$1 d
  shift
  mkdir -p "$out"
  for d in "$@"; do
    [[ -d $d ]] || continue
    cp -r "$d"/. "$out"/
  done
}

# write a flattened POM
#   jb_pom <file> <groupId> <artifactId> <version> [-p packaging] [-n name] -- deps...
jb_pom() {
  local file=$1 g=$2 a=$3 v=$4 packaging=jar name=
  shift 4
  while (( $# )); do
    case $1 in
      -p) packaging=$2; shift 2 ;;
      -n) name=$2; shift 2 ;;
      --) shift; break ;;
      *) _jb_die "jb_pom: unexpected $1"; return 1 ;;
    esac
  done
  local s dv
  {
    echo '<?xml version="1.0" encoding="UTF-8"?>'
    echo '<!-- flattened by javabuild: dependencies pinned to the packaged versions -->'
    echo '<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">'
    echo '  <modelVersion>4.0.0</modelVersion>'
    echo "  <groupId>$g</groupId>"
    echo "  <artifactId>$a</artifactId>"
    echo "  <version>$v</version>"
    [[ $packaging != jar ]] && echo "  <packaging>$packaging</packaging>"
    [[ -n $name ]] && echo "  <name>$name</name>"
    if (( $# )); then
      echo '  <dependencies>'
      for s in "$@"; do
        _jb_spec "$s" || return 1
        if [[ -n $_v ]]; then
          dv=$_v
        else
          _jb_locate "$_g" "$_a" || return 1
          dv=$_ver
        fi
        echo '    <dependency>'
        echo "      <groupId>$_g</groupId>"
        echo "      <artifactId>$_a</artifactId>"
        echo "      <version>$dv</version>"
        [[ -n $_c ]] && echo "      <classifier>$_c</classifier>"
        [[ $_s != compile ]] && echo "      <scope>$_s</scope>"
        [[ -n $_o ]] && echo '      <optional>true</optional>'
        if [[ -n $_x ]]; then
          echo '      <exclusions>'
          local xe
          for xe in $_x; do
            echo '        <exclusion>'
            echo "          <groupId>${xe%%:*}</groupId>"
            echo "          <artifactId>${xe#*:}</artifactId>"
            echo '        </exclusion>'
          done
          echo '      </exclusions>'
        fi
        echo '    </dependency>'
      done
      echo '  </dependencies>'
    fi
    echo '</project>'
  } > "$file"
}

# build a jar from a class directory
#   jb_jar <jar> <classes-dir> [Manifest-Key: value]...
#   JB_UPSTREAM_POM=<pom.xml> with JB_GAV=g:a:v embeds the upstream POM as
#   META-INF/maven/g/a/pom.xml + pom.properties, as Maven does.
jb_jar() {
  local jar=$1 classes=$2
  shift 2
  local mf
  mf=$(mktemp "${srcdir:-/tmp}/jb-manifest.XXXXXX")
  {
    echo "Manifest-Version: 1.0"
    echo "Created-By: javabuild (msys2-ur java-build-helper)"
    local l
    for l in "$@"; do echo "$l"; done
    if [[ -n ${JB_GAV:-} ]]; then
      # unless a merged manifest (OSGi instructions) has its own
      grep -qi '^Implementation-Title:' "$classes/META-INF/MANIFEST.MF" 2>/dev/null \
        || echo "Implementation-Title: $(cut -d: -f2 <<< "$JB_GAV")"
      grep -qi '^Implementation-Version:' "$classes/META-INF/MANIFEST.MF" 2>/dev/null \
        || echo "Implementation-Version: $(cut -d: -f3 <<< "$JB_GAV")"
    fi
    # a manifest shipped in the resources (Maven's <manifestFile>) is merged
    if [[ -f $classes/META-INF/MANIFEST.MF ]]; then
      tr -d '\r' < "$classes/META-INF/MANIFEST.MF" | grep -v -e '^Manifest-Version:' -e '^$'
    fi
  } > "$mf"
  rm -f "$classes/META-INF/MANIFEST.MF"
  if [[ -n ${JB_GAV:-} ]]; then
    local g a v
    IFS=: read -r g a v <<< "$JB_GAV"
    local md="$classes/META-INF/maven/$g/$a"
    mkdir -p "$md"
    [[ -n ${JB_UPSTREAM_POM:-} ]] && cp "$JB_UPSTREAM_POM" "$md/pom.xml"
    printf 'artifactId=%s\ngroupId=%s\nversion=%s\n' "$a" "$g" "$v" > "$md/pom.properties"
  fi
  local -a date=()
  if [[ -n ${SOURCE_DATE_EPOCH:-} ]]; then
    date=(--date="$(date -u -d "@$SOURCE_DATE_EPOCH" +%Y-%m-%dT%H:%M:%SZ)")
  fi
  mkdir -p "$(dirname "$jar")"
  rm -f "$jar"
  jar --create --file "$(jb_w "$jar")" --manifest "$(jb_w "$mf")" "${date[@]}" \
    -C "$(jb_w "$classes")" .
  local rc=$?
  rm -f "$mf"
  return $rc
}

# put an artifact into the build-local repository
#   jb_stage <groupId:artifactId:version> <pom> [<jar> [<classifier>=<jar>...]]
jb_stage() {
  local g a v
  IFS=: read -r g a v <<< "$1"
  local d="$JB_STAGE/${g//.//}/$a/$v"
  mkdir -p "$d"
  cp "$2" "$d/$a-$v.pom"
  if [[ -n ${3:-} ]]; then
    cp "$3" "$d/$a-$v.jar"
  fi
  shift 3 2>/dev/null || shift $#
  local c
  for c in "$@"; do
    cp "${c#*=}" "$d/$a-$v-${c%%=*}.jar"
  done
}

# one-call module build: compile, add resources, jar, write POM, stage.
#   jb_module <g:a:v> <srcdir|-> [options] -- deps...
#     -r DIR        resource directory (repeatable)
#     -s DIR        extra source directory (repeatable)
#     -P PROC       annotation processor (sisu, plexus, mojo=FILE), repeatable
#     -j OPT        extra javac option (repeatable)
#     -m 'K: V'     manifest line (repeatable)
#     -u POM        upstream pom.xml to embed in the jar
#     -p PACKAGING  POM packaging (default jar; maven-plugin for plugins)
#     -c SPEC       compile-only classpath entry (not written to the POM)
#     -C PATH       compile-only classpath file/directory
#     -v REL:DIR    multi-release sources compiled with --release REL into
#                   META-INF/versions/REL (repeatable, in ascending order);
#                   RELt:DIR uses -source/-target REL instead of --release
#     -e PATH       remove PATH (relative to the class directory) before jarring
#     -x REGEX      leave out source files whose path matches REGEX (repeatable)
#     -o DIR        output directory (default $srcdir/jb-build/<artifactId>)
#     -b BND        OSGi metadata from bnd-style instructions (see jb_bnd); the
#                   bundle can then be installed into the Eclipse plugins
#                   directory with jb_install --plugin
#   leaves the jar at $JB_OUT/<artifactId>.jar and classes in $JB_OUT/classes
jb_module() {
  local gav=$1 src=$2
  shift 2
  local g a v
  IFS=: read -r g a v <<< "$gav"
  local -a res=() srcs=() procs=() jopts=() mf=() cpo=() cpx=() deps=() mr=() rmp=()
  local upom= packaging=jar out="${srcdir:-$PWD}/jb-build/$a" xre= bnd=
  [[ $src != - ]] && srcs+=("$src")
  while (( $# )); do
    case $1 in
      -r) res+=("$2"); shift 2 ;;
      -s) srcs+=("$2"); shift 2 ;;
      -P) procs+=("$2"); shift 2 ;;
      -j) jopts+=("$2"); shift 2 ;;
      -m) mf+=("$2"); shift 2 ;;
      -u) upom=$2; shift 2 ;;
      -p) packaging=$2; shift 2 ;;
      -c) cpo+=("$2"); shift 2 ;;
      -C) cpx+=("$2"); shift 2 ;;
      -o) out=$2; shift 2 ;;
      -v) mr+=("$2"); shift 2 ;;
      -e) rmp+=("$2"); shift 2 ;;
      -x) xre="${xre:+$xre|}$2"; shift 2 ;;
      -b) bnd=$2; shift 2 ;;
      --) shift; deps=("$@"); break ;;
      *) _jb_die "jb_module: unexpected '$1'"; return 1 ;;
    esac
  done
  JB_OUT=$out
  rm -rf "${out:?}/classes"
  mkdir -p "$out/classes"
  # resources first: processors merge with resource-provided metadata
  jb_resources "$out/classes" "${res[@]}"
  local -a cpdeps=() d
  for d in "${deps[@]}" "${cpo[@]}"; do
    _jb_spec "$d" || return 1
    [[ $_s == test ]] && continue
    # =version: not packaged, POM only (optional run-time lookups)
    [[ -n $_v ]] && continue
    cpdeps+=("$_g:$_a${_c:+#$_c}${_x:+!${_x// /!}}")
  done
  local cp
  cp=$(jb_cp "${cpdeps[@]}" -- "${cpx[@]}") || return 1
  local -a popts=()
  if (( ${#procs[@]} )); then
    mapfile -t popts < <(jb_processor_opts "${procs[@]}") || return 1
  else
    popts=(-proc:none)
  fi
  if (( ${#srcs[@]} )); then
    JB_SRC_EXCLUDE=$xre jb_javac -d "$(jb_w "$out/classes")" ${cp:+-cp "$cp"} "${popts[@]}" "${jopts[@]}" \
      -- "${srcs[@]}" || return 1
  fi
  # (loop variables must not shadow $v, the version written to the POM)
  local ve rel vdir
  for ve in "${mr[@]}"; do
    rel=${ve%%:*}
    [[ -d ${ve#*:} ]] || { _jb_die "jb_module: no directory ${ve#*:}"; return 1; }
    # a versioned directory that only holds module-info.java
    if [[ ${JB_MODULE_INFO:-0} != 1 ]] \
       && [[ -z $(find "${ve#*:}" -name '*.java' ! -name module-info.java -print -quit) ]]; then
      continue
    fi
    # REL with a trailing t: -source/-target REL against the running JDK's
    # API (Gradle's sourceCompatibility/targetCompatibility) instead of --release
    local tgt=
    if [[ $rel == *t ]]; then rel=${rel%t}; tgt=$rel; fi
    vdir="$out/classes/META-INF/versions/$rel"
    mkdir -p "$vdir"
    JB_TARGET=$tgt JB_RELEASE=$rel jb_javac -d "$(jb_w "$vdir")" \
      -cp "$(jb_w "$out/classes")${cp:+;$cp}" -proc:none "${jopts[@]}" -- "${ve#*:}" || return 1
  done
  for ve in "${rmp[@]}"; do
    rm -rf "${out:?}/classes/${ve:?}"
  done
  # versioned classes present?
  [[ -d $out/classes/META-INF/versions ]] && mf+=("Multi-Release: true")
  # module-info.java is not compiled; keep its module name for the jar
  if [[ ${JB_MODULE_INFO:-0} != 1 ]] && ! printf '%s\n' "${mf[@]}" | grep -q '^Automatic-Module-Name:'; then
    local mi modname
    for ve in "${srcs[@]}" "${mr[@]#*:}"; do
      [[ -d $ve ]] || continue
      mi=$(find "$ve" -maxdepth 1 -name module-info.java -print -quit)
      [[ -n $mi ]] || continue
      modname=$(sed -n 's/^\s*\(open \)\?module \+\([A-Za-z0-9_.]\+\).*/\2/p' "$mi" | head -1)
      [[ -n $modname ]] && { mf+=("Automatic-Module-Name: $modname"); break; }
    done
  fi
  if [[ -n $bnd ]]; then
    jb_bnd "$out/classes" "$bnd" "$out/classes/META-INF/MANIFEST.MF" "$cp" -D "project.version=$v" || return 1
  fi
  JB_GAV=$gav JB_UPSTREAM_POM=$upom jb_jar "$out/$a.jar" "$out/classes" "${mf[@]}" || return 1
  jb_pom "$out/$a.pom" "$g" "$a" "$v" -p "$packaging" -- "${deps[@]}" || return 1
  jb_stage "$gav" "$out/$a.pom" "$out/$a.jar"
}

# write the properties file read by the plugin.xml processor
#   jb_plugin_props <file> <g:a:v> <goalPrefix> <name> <description> [k=v...]
#   dependencies are taken from the staged/installed POM closure of DEPS
#   given after --:  jb_plugin_props f gav prefix name desc -- deps...
jb_plugin_props() {
  local file=$1 gav=$2 prefix=$3 name=$4 desc=$5
  shift 5
  local g a v
  IFS=: read -r g a v <<< "$gav"
  local -a kv=()
  while (( $# )) && [[ $1 != -- ]]; do kv+=("$1"); shift; done
  [[ ${1:-} == -- ]] && shift
  {
    printf 'groupId=%s\nartifactId=%s\nversion=%s\ngoalPrefix=%s\n' "$g" "$a" "$v" "$prefix"
    printf 'name=%s\ndescription=%s\n' "$name" "$desc"
    local l
    for l in "${kv[@]}"; do echo "$l"; done
    local i=0 s spec
    local -a direct=()
    for spec in "$@"; do
      _jb_spec "$spec" || return 1
      [[ $_s == compile || $_s == runtime ]] && [[ -z $_o ]] && direct+=("$_g:$_a${_x:+!${_x// /!}}")
    done
    if (( ${#direct[@]} )); then
      while read -r s; do
        _jb_spec "$s" || return 1
        _jb_locate "$_g" "$_a" || return 1
        echo "dependency.$i=$_g:$_a:jar:$_ver"
        i=$((i + 1))
      done < <(jb_closure "${direct[@]}")
    fi
  } > "$file"
}

# install staged artifacts into $pkgdir
#   jb_install [--jar NAME] [--plugin] groupId:artifactId...
#   the jar is also linked as share/java/<artifactId>.jar, or NAME.jar with
#   --jar (for artifactIds that exist under several groupIds); with --plugin
#   (OSGi bundles) also as lib/eclipse/plugins/<bsn>_<version>.jar
jb_install() {
  local jarname= plugin=
  while [[ ${1:-} == --* ]]; do
    case $1 in
      --jar) jarname=$2; shift 2 ;;
      --plugin) plugin=1; shift ;;
      *) break ;;
    esac
  done
  local s f
  for s in "$@"; do
    _jb_spec "$s" || return 1
    local d="$JB_STAGE/${_g//.//}/$_a"
    local -a vs=("$d"/*/)
    (( ${#vs[@]} == 1 )) && [[ -d ${vs[0]} ]] || _jb_die "$s is not staged (once)" || return 1
    local v=${vs[0]%/}
    v=${v##*/}
    local dest="$pkgdir$JB_SYSREPO/${_g//.//}/$_a/$v"
    install -d "$dest"
    for f in "$d/$v"/*; do
      install -m644 "$f" "$dest/"
    done
    if [[ -f $dest/$_a-$v.jar ]]; then
      local link="$pkgdir$MINGW_PREFIX/share/java/${jarname:-$_a}.jar"
      install -d "$pkgdir$MINGW_PREFIX/share/java"
      ln -f "$dest/$_a-$v.jar" "$link" 2>/dev/null || install -m644 "$dest/$_a-$v.jar" "$link"
      if [[ -n $plugin ]]; then
        local bv
        bv=$(_jb_osgi bsnver "$(jb_w "$dest/$_a-$v.jar")") || return 1
        [[ $bv != null* ]] || _jb_die "$s has no Bundle-SymbolicName" || return 1
        bv=${bv// /_}
        install -d "$pkgdir$JB_PLUGINS"
        ln -f "$dest/$_a-$v.jar" "$pkgdir$JB_PLUGINS/${bv%$'\r'}.jar" 2>/dev/null \
          || install -m644 "$dest/$_a-$v.jar" "$pkgdir$JB_PLUGINS/${bv%$'\r'}.jar"
      fi
    fi
  done
}

# smoke test: load every class of staged artifacts against their dependencies
#   jb_loadcheck [--ignore REGEX] [--with SPEC]... groupId:artifactId[#classifier]...
#   --with adds provided-scope artifacts (what Maven's core realm supplies)
jb_loadcheck() {
  local -a ign=() with=()
  while (( $# )); do
    case $1 in
      --ignore) ign=(--ignore "$2"); shift 2 ;;
      --with) with+=("$2"); shift 2 ;;
      *) break ;;
    esac
  done
  local s jar cp
  for s in "$@"; do
    jar=$(jb_jarpath "$s") || return 1
    cp=$(jb_cp "$s" "${with[@]}") || return 1
    java -cp "$(jb_w "$JB_HOME/javabuild.jar")" jb.LoadCheck "${ign[@]}" \
      "$(jb_w "$jar")" "$cp" || return 1
  done
}

# run JUnit 4 tests
#   jb_junit4 <test-classes-dir> <classpath> [-x Class[#methodRegex]]... [TestClass...]
#   without class names every concrete *Test / Test* / *Tests class is run;
#   -x excludes a test class or the matching test methods of a class.
jb_junit4() {
  local dir=$1 cp=$2
  shift 2
  local -a classes=() excl=()
  while (( $# )); do
    if [[ $1 == -x ]]; then excl+=(-x "$2"); shift 2; else classes+=("$1"); shift; fi
  done
  if (( ${#classes[@]} == 0 )); then
    excl=(-auto "${excl[@]}")
    mapfile -t classes < <(cd "$dir" && find . -name '*.class' ! -name '*$*' \
      \( -name '*Test.class' -o -name 'Test*.class' -o -name '*Tests.class' \) \
      | sed 's|^\./||; s|\.class$||; s|/|.|g' | sort)
  fi
  (( ${#classes[@]} )) || { echo "javabuild: no tests in $dir"; return 0; }
  local junit runner="${srcdir:-/tmp}/jb-junit4runner"
  junit=$(jb_cp junit:junit) || return 1
  if [[ ! -f $runner/jb/JUnit4Runner.class ]]; then
    mkdir -p "$runner"
    javac --release 8 -nowarn -Xlint:-options -proc:none -d "$(jb_w "$runner")" -cp "$junit" \
      "$(jb_w "$JB_HOME/JUnit4Runner.java")" || return 1
  fi
  # like surefire: run in the project directory with ${basedir} and target/
  mkdir -p target
  java -Dbasedir="$(jb_w "$PWD")" -cp "$(jb_w "$dir");$cp;$junit;$(jb_w "$runner")" \
    jb.JUnit4Runner "${excl[@]}" "${classes[@]}"
}

# regex of the sources under DIR whose text matches REGEX, plus (transitively)
# those that mention their class names
_jb_users() {
  local dir=$1 re=$2
  local -A seen=()
  local -a files new
  mapfile -t files < <(grep -rlE "$re" "$dir" --include='*.java')
  while (( ${#files[@]} )); do
    new=()
    local f n
    for f in "${files[@]}"; do
      [[ -n ${seen[$f]:-} ]] && continue
      seen[$f]=1
      new+=("$(basename "$f" .java)")
    done
    (( ${#new[@]} )) || break
    local IFS='|'
    mapfile -t files < <(grep -rlwE "(${new[*]})" "$dir" --include='*.java')
    unset IFS
  done
  local -a names=()
  for f in "${!seen[@]}"; do names+=("/$(basename "$f" .java)\\.java\$"); done
  local IFS='|'
  echo "${names[*]}"
}

# compile and run upstream JUnit 4 tests
#   jb_test <name> <test-src-dir> [options] -- specs...
#     -r DIR        test resources (copied next to the test classes)
#     -x REGEX      leave out test sources whose path matches REGEX
#     -g REGEX      leave out test sources whose text matches REGEX (e.g.
#                   'org\.mockito'), and the sources that use those classes
#     -X EXCL       exclude a test class / Class#methodRegex at run time
#     -C PATH       extra classpath entry (class directory or jar)
#     -t CLASS      run only these test classes (repeatable)
#   specs: the artifacts under test and their test dependencies (JUnit is
#   added automatically)
jb_test() {
  local name=$1 src=$2
  shift 2
  local -a res=() excl=() cpx=() specs=() only=()
  local xre=
  while (( $# )); do
    case $1 in
      -r) res+=("$2"); shift 2 ;;
      -x) xre="${xre:+$xre|}$2"; shift 2 ;;
      -X) excl+=(-x "$2"); shift 2 ;;
      -C) cpx+=("$2"); shift 2 ;;
      -t) only+=("$2"); shift 2 ;;
      -g) local gx
          gx=$(_jb_users "$src" "$2") || return 1
          [[ -n $gx ]] && xre="${xre:+$xre|}$gx"
          shift 2 ;;
      --) shift; specs=("$@"); break ;;
      *) _jb_die "jb_test: unexpected '$1'"; return 1 ;;
    esac
  done
  local t="${srcdir:-$PWD}/jb-test/$name"
  rm -rf "$t"
  mkdir -p "$t"
  jb_resources "$t" "${res[@]}"
  local cp
  cp=$(jb_cp "${specs[@]}" junit:junit -- "${cpx[@]}") || return 1
  JB_SRC_EXCLUDE=$xre jb_javac -d "$(jb_w "$t")" -cp "$cp" -proc:none -- "$src" || return 1
  jb_junit4 "$t" "$cp" "${excl[@]}" "${only[@]}"
}

# generate sources from a Modello model, as the modello-maven-plugin would
#   jb_modello <model.mdo> <output-dir> <model-version> <mode>... [-- key=value...]
#   modes: java, xpp3-reader, xpp3-writer, xpp3-extended-reader, ...
#   runs jb.ModelloRunner (the plugin's default parameters) on Modello
jb_modello() {
  local mdo=$1 out=$2 ver=$3
  shift 3
  local -a modes=() extra=()
  while (( $# )); do
    if [[ $1 == -- ]]; then shift; extra=("$@"); break; fi
    modes+=("$1"); shift
  done
  local cp mode
  cp=$(jb_cp org.codehaus.modello:modello-plugin-xpp3) || return 1
  mkdir -p "$out"
  for mode in "${modes[@]}"; do
    echo "javabuild: modello $mode $(basename "$mdo") $ver"
    java -cp "$(jb_w "$JB_HOME/javabuild.jar");$cp" jb.ModelloRunner "$(jb_w "$mdo")" "$mode" \
      "$(jb_w "$out")" "$ver" "${extra[@]}" || return 1
  done
}

# build a Maven plugin: jb_module with the plugin.xml processor
#   jb_plugin <g:a:v> <goalPrefix> <name> <requiredJavaVersion> <requiredMavenVersion> \
#             <srcdir> [jb_module options] -- deps...
#   the plugin's provided dependencies (maven-plugin-api, maven-core,
#   maven-plugin-annotations, ...) belong in deps with /provided
jb_plugin() {
  local gav=$1 prefix=$2 name=$3 rjava=$4 rmaven=$5 src=$6
  shift 6
  local -a opts=() deps=()
  while (( $# )); do
    if [[ $1 == -- ]]; then shift; deps=("$@"); break; fi
    opts+=("$1"); shift
  done
  local a props
  a=$(cut -d: -f2 <<< "$gav")
  props="${srcdir:-$PWD}/jb-build/$a.plugin.properties"
  mkdir -p "$(dirname "$props")"
  jb_plugin_props "$props" "$gav" "$prefix" "$name" "$name" \
    "requiredJavaVersion=$rjava" "requiredMavenVersion=$rmaven" -- "${deps[@]}" || return 1
  jb_module "$gav" "$src" -p maven-plugin -P "mojo=$props" "${opts[@]}" -- "${deps[@]}"
}

# merge jars and relocate packages, as maven-shade-plugin's relocations do
#   jb_relocate <out.jar> [-r from.package=to.package]... -- specs-or-jars...
#   specs are resolved to their jars (without dependencies); runs
#   jb.Relocate, compiled against the packaged ASM
jb_relocate() {
  local out=$1
  shift
  local -a rules=() ins=()
  while (( $# )); do
    case $1 in
      -r) rules+=(-r "$2"); shift 2 ;;
      --) shift; break ;;
      *) _jb_die "jb_relocate: unexpected '$1'"; return 1 ;;
    esac
  done
  local s
  for s in "$@"; do
    if [[ -f $s ]]; then ins+=("$(jb_w "$s")"); else ins+=("$(jb_w "$(jb_jarpath "$s")")") || return 1; fi
  done
  local asm tool="${srcdir:-/tmp}/jb-relocate"
  asm=$(jb_cp org.ow2.asm:asm-commons) || return 1
  if [[ ! -f $tool/jb/Relocate.class ]]; then
    mkdir -p "$tool"
    javac --release 11 -nowarn -proc:none -d "$(jb_w "$tool")" -cp "$asm" \
      "$(jb_w "$JB_HOME/Relocate.java")" || return 1
  fi
  mkdir -p "$(dirname "$out")"
  java -cp "$(jb_w "$tool");$asm" jb.Relocate "$(jb_w "$out")" "${rules[@]}" "${ins[@]}"
}

# ======================================================================
# OSGi bundles (Eclipse plug-ins)
#
# Eclipse bundles are built from their own META-INF/MANIFEST.MF and
# build.properties, as PDE build / Tycho do, but with javac:
#   * source.<library> folders are compiled (jars.compile.order), with the
#     non-Java files of the source folders copied next to the classes;
#   * bin.includes / bin.excludes decide the content of the bundle;
#   * ".qualifier" in Bundle-Version is replaced by a fixed qualifier
#     ($JB_QUALIFIER, per pkgbase);
#   * Declarative Services XML is generated by jb.DsProcessor when PDE's DS
#     annotation support is enabled for the project;
#   * the compile class path is the closure of Require-Bundle,
#     Import-Package and Fragment-Host over the staged bundles of this build
#     ($JB_PSTAGE) and the installed ones ($JB_PLUGINS), plus the fragments
#     of the hosts in it (the SWT win32 fragment).
# Bundles are staged as $JB_PSTAGE/<bsn>_<version>.jar and installed into
#   ${MINGW_PREFIX}/lib/eclipse/plugins/<bsn>_<version>.jar
# (or the unpacked directory for Eclipse-BundleShape: dir).
# ======================================================================

JB_PLUGINS="${MINGW_PREFIX}/lib/eclipse/plugins"
JB_PSTAGE="${srcdir:-$PWD}/jb-plugins"
: "${JB_QUALIFIER:=}"

_jb_osgi() {
  java -cp "$(jb_w "$JB_HOME/javabuild.jar")" jb.Osgi "$@" | tr -d '\r'
  return "${PIPESTATUS[0]}"
}

# plug-in directories searched for dependencies (Windows form)
_jb_pdirs() {
  echo "$(jb_w "$JB_PSTAGE");$(jb_w "$JB_PLUGINS")${JB_PLUGINS_EXTRA:+;$JB_PLUGINS_EXTRA}"
}

# compile classpath of a bundle manifest:  jb_osgi_cp MANIFEST [--extra BSN]...
jb_osgi_cp() {
  local mf=$1
  shift
  mkdir -p "${srcdir:-$PWD}/jb-nested"
  _jb_osgi classpath --dirs "$(_jb_pdirs)" --nested "$(jb_w "${srcdir:-$PWD}/jb-nested")" "$@" "$(jb_w "$mf")"
}

# --release for a manifest's Bundle-RequiredExecutionEnvironment
_jb_bree_release() {
  local bree req v
  bree=$(_jb_osgi header "$(jb_w "$1")" Bundle-RequiredExecutionEnvironment)
  bree=${bree%%,*}
  if [[ -z $bree ]]; then
    req=$(_jb_osgi header "$(jb_w "$1")" Require-Capability)
    if [[ $req =~ osgi\.ee=JavaSE\)\(version=([0-9.]+)\) ]]; then
      bree="JavaSE-${BASH_REMATCH[1]}"
    fi
  fi
  case $bree in
    JavaSE-1.[0-8]|J2SE-*|JRE-*|CDC-*|OSGi/Minimum-*|"") v=8 ;;
    JavaSE-*) v=${bree#JavaSE-} ;;
    *) v=8 ;;
  esac
  echo "$v"
}

# expand a bin.includes pattern relative to the bundle directory
_jb_glob() {
  local base=$1 pat=$2
  (
    cd "$base" || exit 1
    shopt -s nullglob globstar dotglob
    # shellcheck disable=SC2206
    local m=($pat) f
    for f in "${m[@]}"; do [[ -e $f ]] && printf '%s\n' "$f"; done
  )
}

# build a bundle from its project directory
#   jb_bundle <bundle-dir> [options]
#     -q QUAL     qualifier (default $JB_QUALIFIER)
#     -C PATH     extra compile classpath entry (jar or directory)
#     -E BSN      extra bundle on the compile classpath (as additional.bundles)
#     -j OPT      extra javac option (repeatable)
#     -x REGEX    leave out source files whose path matches REGEX
#     -r REL      --release (default from Bundle-RequiredExecutionEnvironment)
#     -H 'K: V'   set a manifest header
#     -R NAME     remove a manifest header
#     -a SRC=DEST add a file to the bundle (e.g. a native library)
#     -L LIB      leave out the library LIB (source.LIB and its bin.includes entry)
#     -n          no Declarative Services processing
#     -D          Declarative Services processing even without PDE settings
#   stages $JB_PSTAGE/<bsn>_<version>.jar and sets JB_BUNDLE_JAR/JB_BSN/JB_BVER
jb_bundle() {
  local dir=$1
  shift
  local qual=$JB_QUALIFIER rel= ds=auto xre=
  local -a cpx=() extra=() jopts=() hset=() hrm=() adds=() skip=()
  while (( $# )); do
    case $1 in
      -q) qual=$2; shift 2 ;;
      -C) cpx+=("$2"); shift 2 ;;
      -E) extra+=(--extra "$2"); shift 2 ;;
      -j) jopts+=("$2"); shift 2 ;;
      -x) xre="${xre:+$xre|}$2"; shift 2 ;;
      -r) rel=$2; shift 2 ;;
      -H) hset+=(--set "$2"); shift 2 ;;
      -R) hrm+=(--remove "$2"); shift 2 ;;
      -a) adds+=("$2"); shift 2 ;;
      -L) skip+=("$2"); shift 2 ;;
      -n) ds=no; shift ;;
      -D) ds=yes; shift ;;
      *) _jb_die "jb_bundle: unexpected '$1'"; return 1 ;;
    esac
  done
  local mf="$dir/META-INF/MANIFEST.MF" bp="$dir/build.properties"
  [[ -f $mf ]] || _jb_die "jb_bundle: no $mf" || return 1
  local bv bsn ver
  bv=$(_jb_osgi bsnver "$(jb_w "$mf")") || return 1
  bsn=${bv% *}
  ver=${bv#* }
  ver=${ver/qualifier/$qual}
  ver=${ver%.}
  [[ -n $qual || $ver != *qualifier* ]] || _jb_die "jb_bundle: $bsn needs a qualifier (JB_QUALIFIER)" || return 1
  echo "javabuild: bundle $bsn $ver"
  local out="${srcdir:-$PWD}/jb-bundles/$bsn"
  rm -rf "$out"
  mkdir -p "$out/root" "$JB_PSTAGE"
  rm -f "$JB_PSTAGE/${bsn}_"*.jar

  local -a libs=() order=()
  if [[ -f $bp ]]; then
    mapfile -t libs < <(_jb_osgi keys "$(jb_w "$bp")" source.)
    mapfile -t order < <(_jb_osgi props "$(jb_w "$bp")" jars.compile.order)
    local e
    while read -r e; do
      [[ -n $e ]] && extra+=(--extra "$e")
    done < <(_jb_osgi props "$(jb_w "$bp")" additional.bundles)
  fi
  # compile order: jars.compile.order, then "." , then the rest
  local -a sorted=() l
  for l in "${order[@]}"; do sorted+=("source.$l"); done
  for l in source.. "${libs[@]}"; do
    [[ " ${libs[*]} " == *" $l "* ]] || continue
    [[ " ${sorted[*]} " == *" $l "* ]] || sorted+=("$l")
  done
  local -a kept=()
  for l in "${sorted[@]}"; do
    [[ " ${skip[*]} " == *" ${l#source.} "* ]] || kept+=("$l")
  done
  sorted=("${kept[@]}")

  [[ -n $rel ]] || rel=$(_jb_bree_release "$mf")
  # like PDE/Tycho, every plug-in compiles against the OSGi annotations
  # (versioning, bundle, Declarative Services), whether it imports them or not
  extra+=(--extra-optional org.osgi.service.component.annotations)
  local ann
  if ann=$(jb_jarpath org.osgi:osgi.annotation 2>/dev/null); then cpx+=("$ann"); fi
  # and projects with the API tools nature against the PDE API annotations
  # (@NoImplement, @NoExtend, ...)
  if [[ -f $dir/.project ]] && grep -q 'org.eclipse.pde.api.tools.apiAnalysisNature' "$dir/.project"; then
    extra+=(--extra-optional org.eclipse.pde.api.tools.annotations)
  fi
  local cp
  cp=$(jb_osgi_cp "$mf" "${extra[@]}") || return 1
  # jars.extra.classpath: bundle-relative paths or platform:/plugin/<bsn>/<path>
  if [[ -f $bp ]]; then
    local x
    while read -r x; do
      [[ -n $x ]] || continue
      if [[ $x == platform:/plugin/* ]]; then
        local rest=${x#platform:/plugin/} pb pj
        pb=${rest%%/*}
        pj=$(ls -d "$JB_PSTAGE/${pb}_"* "$JB_PLUGINS/${pb}_"* 2>/dev/null | head -1)
        [[ -n $pj ]] && cpx+=("$pj")
      elif [[ -e $dir/$x ]]; then
        cpx+=("$dir/$x")
      fi
    done < <(_jb_osgi props "$(jb_w "$bp")" jars.extra.classpath)
  fi
  for x in "${cpx[@]}"; do cp="${cp:+$cp;}$(jb_w "$x")"; done

  # Declarative Services
  local dsprefs="$dir/.settings/org.eclipse.pde.ds.annotations.prefs" dspath=OSGI-INF
  if [[ $ds == auto ]]; then
    ds=no
    if [[ -f $dsprefs ]] && grep -q '^enabled=true' "$dsprefs"; then ds=yes; fi
  fi
  if [[ -f $dsprefs ]] && grep -q '^path=' "$dsprefs"; then
    dspath=$(sed -n 's/^path=//p' "$dsprefs" | tr -d '\r')
  fi
  local -a popts=(-proc:none)
  if [[ $ds == yes ]]; then
    : > "$out/ds.list"
    popts=(-processor jb.DsProcessor -processorpath "$(jb_w "$JB_HOME/javabuild.jar")"
           "-Ajb.ds.path=$dspath" "-Ajb.ds.list=$(jb_w "$out/ds.list")")
  fi

  # compile every library
  local lib libout srcs s
  local -a srcdirs
  local libcp=$cp
  for l in "${sorted[@]}"; do
    lib=${l#source.}
    if [[ $lib == . ]]; then libout="$out/classes"; else libout="$out/lib/$lib"; fi
    mkdir -p "$libout"
    mapfile -t srcdirs < <(_jb_osgi props "$(jb_w "$bp")" "$l")
    local -a existing=()
    for s in "${srcdirs[@]}"; do
      s=${s%/}
      [[ -d $dir/$s ]] && existing+=("$dir/$s")
    done
    (( ${#existing[@]} )) || continue
    if [[ -n $(find "${existing[@]}" -name '*.java' -print -quit) ]]; then
      local -a po=("${popts[@]}")
      [[ $lib == . ]] || po=(-proc:none)
      JB_TARGET= JB_RELEASE=$rel JB_SRC_EXCLUDE=$xre jb_javac -d "$(jb_w "$libout")" \
        ${libcp:+-cp "$libcp"} "${po[@]}" "${jopts[@]}" -- "${existing[@]}" || return 1
    fi
    # resources of the source folders, without exclude.<library> patterns
    # and $JB_RESOURCE_EXCLUDES (file name globs; package.html by default, as
    # eclipse-platform-parent's tycho-compiler configuration has it)
    local -a rx=()
    local xp
    for xp in ${JB_RESOURCE_EXCLUDES-package.html}; do rx+=(! -name "$xp"); done
    while read -r xp; do
      [[ -n $xp ]] || continue
      xp=${xp//\*\*\//*/}
      xp=${xp//\/\*\*/\/*}
      rx+=(! -path "./${xp#./}")
    done < <(_jb_osgi props "$(jb_w "$bp")" "exclude.$lib")
    for s in "${existing[@]}"; do
      (cd "$s" && find . -type f ! -name '*.java' "${rx[@]}" \
        -exec cp --parents -t "$libout" {} +) || return 1
    done
    libcp="$(jb_w "$libout")${libcp:+;$libcp}"
  done

  # bundle content: bin.includes
  local -a incs=() excs=()
  if [[ -f $bp ]]; then
    mapfile -t incs < <(_jb_osgi props "$(jb_w "$bp")" bin.includes)
    mapfile -t excs < <(_jb_osgi props "$(jb_w "$bp")" bin.excludes)
  else
    incs=(. META-INF/)
  fi
  local inc f
  for inc in "${incs[@]}"; do
    inc=${inc%/}
    [[ " ${skip[*]} " == *" $inc "* ]] && continue
    if [[ $inc == . || $inc == @dot ]]; then
      [[ -d $out/classes ]] && cp -r "$out/classes"/. "$out/root"/
    elif [[ -d $out/lib/$inc ]]; then
      mkdir -p "$(dirname "$out/root/$inc")"
      jar --create --file "$(jb_w "$out/root/$inc")" -C "$(jb_w "$out/lib/$inc")" . || return 1
    else
      while read -r f; do
        [[ -n $f ]] || continue
        mkdir -p "$(dirname "$out/root/$f")"
        cp -r "$dir/$f" "$(dirname "$out/root/$f")"/
      done < <(_jb_glob "$dir" "$inc")
    fi
  done
  for inc in "${excs[@]}"; do
    while read -r f; do
      [[ -n $f ]] && rm -rf "${out:?}/root/$f"
    done < <(_jb_glob "$out/root" "${inc%/}")
  done
  for inc in "${adds[@]}"; do
    mkdir -p "$(dirname "$out/root/${inc#*=}")"
    cp -r "${inc%%=*}" "$out/root/${inc#*=}"
  done
  rm -f "$out/root/META-INF/MANIFEST.MF"
  find "$out/root" -name '.gitignore' -delete

  # manifest
  if [[ $ds == yes && -s $out/ds.list ]]; then
    local sc
    sc=$(_jb_osgi header "$(jb_w "$mf")" Service-Component)
    if [[ -z $sc ]]; then
      sc=$(sort "$out/ds.list" | tr -d '\r' | paste -sd, -)
      hset+=(--set "Service-Component: $sc")
    fi
  fi
  _jb_osgi manifest "$(jb_w "$mf")" "$(jb_w "$out/MANIFEST.MF")" --qualifier "$qual" \
    "${hset[@]}" "${hrm[@]}" || return 1
  # every component listed in Service-Component must be in the bundle
  local scl
  scl=$(_jb_osgi header "$(jb_w "$out/MANIFEST.MF")" Service-Component)
  if [[ -n $scl ]]; then
    local c
    for c in ${scl//,/ }; do
      [[ $c == *'*'* ]] && continue
      [[ -f $out/root/$c ]] || _jb_die "jb_bundle: $bsn: Service-Component $c is missing" || return 1
    done
  fi
  local -a date=()
  if [[ -n ${SOURCE_DATE_EPOCH:-} ]]; then
    date=(--date="$(date -u -d "@$SOURCE_DATE_EPOCH" +%Y-%m-%dT%H:%M:%SZ)")
  fi
  JB_BUNDLE_JAR="$JB_PSTAGE/${bsn}_${ver}.jar"
  JB_BSN=$bsn
  JB_BVER=$ver
  jar --create --file "$(jb_w "$JB_BUNDLE_JAR")" --manifest "$(jb_w "$out/MANIFEST.MF")" "${date[@]}" \
    -C "$(jb_w "$out/root")" . || return 1
}

# build several bundle directories in dependency order
#   jb_bundles [jb_bundle options for all] -- DIR...
#   JB_BUNDLE_OPTS_<bsn with . and - as _> (an array) adds per-bundle options
jb_bundles() {
  local -a common=() dirs=()
  while (( $# )); do
    if [[ $1 == -- ]]; then shift; dirs=("$@"); break; fi
    common+=("$1"); shift
  done
  local -a ws=()
  local d
  for d in "${dirs[@]}"; do ws+=("$(jb_w "$d")"); done
  local line bsn bdir var
  while IFS=$'\t' read -r bsn bdir; do
    var="JB_BUNDLE_OPTS_${bsn//[.-]/_}[@]"
    jb_bundle "$(cygpath -u "$bdir")" "${common[@]}" "${!var}" || return 1
  done < <(_jb_osgi order "${ws[@]}")
}

# staged jar of a bundle:  jb_bundle_jar BSN
jb_bundle_jar() {
  local f
  f=$(ls -d "$JB_PSTAGE/${1}_"*.jar 2>/dev/null | head -1)
  [[ -n $f ]] || _jb_die "bundle $1 is not staged" || return 1
  echo "$f"
}

# smoke test: load every class of staged bundles against their OSGi class path
#   jb_bundle_loadcheck [--ignore REGEX] BSN...
jb_bundle_loadcheck() {
  local -a ign=()
  if [[ $1 == --ignore ]]; then ign=(--ignore "$2"); shift 2; fi
  local b jar cp tmp
  for b in "$@"; do
    jar=$(jb_bundle_jar "$b") || return 1
    tmp="${srcdir:-/tmp}/jb-lc-$b.MF"
    unzip -p "$jar" META-INF/MANIFEST.MF > "$tmp"
    cp=$(jb_osgi_cp "$tmp") || return 1
    java -cp "$(jb_w "$JB_HOME/javabuild.jar")" jb.LoadCheck "${ign[@]}" "$(jb_w "$jar")" "$cp" || return 1
  done
}

# install staged bundles into $pkgdir:  jb_plugins_install BSN...
#   bundles with Eclipse-BundleShape: dir are installed unpacked
jb_plugins_install() {
  local b jar shape dest
  install -d "$pkgdir$JB_PLUGINS"
  for b in "$@"; do
    jar=$(jb_bundle_jar "$b") || return 1
    shape=$(_jb_osgi header "$(jb_w "$jar")" Eclipse-BundleShape)
    if [[ $shape == dir ]]; then
      dest="$pkgdir$JB_PLUGINS/$(basename "$jar" .jar)"
      install -d "$dest"
      (cd "$dest" && jar --extract --file "$(jb_w "$jar")") || return 1
    else
      install -m644 "$jar" "$pkgdir$JB_PLUGINS/"
    fi
  done
}

# OSGi metadata for a class directory or jar from bnd-style instructions
#   jb_bnd <classes|jar> <instructions> <out-manifest> [<classpath>] [-D k=v]...
jb_bnd() {
  local in=$1 bnd=$2 out=$3 cp=${4:-}
  shift 4 2>/dev/null || shift $#
  local -a defs=()
  while (( $# )); do
    [[ $1 == -D ]] && defs+=(-D "$2")
    shift 2
  done
  mkdir -p "$(dirname "$out")"
  java -cp "$(jb_w "$JB_HOME/javabuild.jar")" jb.Bnd "${defs[@]}" "$(jb_w "$in")" "$(jb_w "$bnd")" \
    "$(jb_w "$out")" "$cp"
}

# turn an installed (non-OSGi) jar into a bundle, as Eclipse Orbit does
#   jb_wrap <spec> <instructions> [-D k=v]...
#   the wrapped bundle is staged in $JB_PSTAGE (install with jb_plugins_install)
jb_wrap() {
  local spec=$1 bnd=$2
  shift 2
  local jar cp v w
  jar=$(jb_jarpath "$spec") || return 1
  v=$(jb_version "$spec") || return 1
  cp=$(jb_cp "$spec") || return 1
  w="${srcdir:-$PWD}/jb-wrap/${spec//:/_}"
  rm -rf "$w"
  mkdir -p "$w/root" "$JB_PSTAGE"
  (cd "$w/root" && jar --extract --file "$(jb_w "$jar")") || return 1
  rm -f "$w/root/META-INF/MANIFEST.MF"
  jb_bnd "$w/root" "$bnd" "$w/MANIFEST.MF" "$cp" -D "project.version=$v" "$@" || return 1
  local bv
  bv=$(_jb_osgi bsnver "$(jb_w "$w/MANIFEST.MF")") || return 1
  local -a date=()
  if [[ -n ${SOURCE_DATE_EPOCH:-} ]]; then
    date=(--date="$(date -u -d "@$SOURCE_DATE_EPOCH" +%Y-%m-%dT%H:%M:%SZ)")
  fi
  JB_BUNDLE_JAR="$JB_PSTAGE/${bv// /_}.jar"
  jar --create --file "$(jb_w "$JB_BUNDLE_JAR")" --manifest "$(jb_w "$w/MANIFEST.MF")" "${date[@]}" \
    -C "$(jb_w "$w/root")" .
}

# resolve staged bundles in Equinox together with the installed plug-ins
#   jb_osgi_resolvecheck [--allow REGEX] [--start BSN]... [BSN...]
#   (default: every staged bundle); fails if one of them stays INSTALLED
jb_osgi_resolvecheck() {
  local -a opts=() sel=()
  while (( $# )); do
    case $1 in
      --allow|--start) opts+=("$1" "$2"); shift 2 ;;
      *) sel+=("$1"); shift ;;
    esac
  done
  local osgi tool="${srcdir:-/tmp}/jb-resolvecheck" store="${srcdir:-/tmp}/jb-resolvecheck-store"
  osgi=$(ls -d "$JB_PSTAGE"/org.eclipse.osgi_*.jar "$JB_PLUGINS"/org.eclipse.osgi_*.jar 2>/dev/null | head -1)
  [[ -n $osgi ]] || _jb_die "jb_osgi_resolvecheck: no org.eclipse.osgi bundle" || return 1
  if [[ ! -f $tool/jb/ResolveCheck.class ]]; then
    mkdir -p "$tool"
    javac --release 11 -nowarn -proc:none -d "$(jb_w "$tool")" -cp "$(jb_w "$osgi")" \
      "$(jb_w "$JB_HOME/ResolveCheck.java")" || return 1
  fi
  local -a files=() staged=()
  local f bv
  local -A have=()
  for f in "$JB_PSTAGE"/*.jar; do
    [[ -e $f ]] || continue
    bv=$(basename "$f" .jar)
    have[${bv%%_*}]=1
    [[ $bv == org.eclipse.osgi_* ]] && continue
    if (( ${#sel[@]} == 0 )) || [[ " ${sel[*]} " == *" ${bv%%_*} "* ]]; then
      staged+=("$(jb_w "$f")")
    else
      files+=("$(jb_w "$f")")
    fi
  done
  for f in "$JB_PLUGINS"/*; do
    [[ -e $f ]] || continue
    bv=$(basename "$f" .jar)
    [[ -n ${have[${bv%%_*}]:-} ]] && continue
    [[ $bv == org.eclipse.osgi_* ]] && continue
    files+=("$(jb_w "$f")")
  done
  rm -rf "$store"
  java -cp "$(jb_w "$osgi");$(jb_w "$tool")" jb.ResolveCheck "${opts[@]}" --check "${#staged[@]}" \
    "$(jb_w "$store")" "${staged[@]}" "${files[@]}"
}
