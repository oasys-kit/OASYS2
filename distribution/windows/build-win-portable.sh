#!/usr/bin/env bash



export PATH="/C/Program Files (x86)/GnuWin32/bin/":$PATH
export PATH="/C/msys64":$PATH
export PATH="/C/Program Files/7-Zip:/C/msys64:/C/Program Files (x86)/GnuWin32/bin/":$PATH
export PATH="/C/Users/lrebuffi/AppData/Local/Programs/Python/Python313/Scripts":$PATH
export PATH="/C/Program Files (x86)/NSIS":$PATH

echo $PATH

NAME=Oasys2
VERSION=2.0

DIR=$(dirname "$0")
FULL_DIR=$(pwd)/${DIR:2}

echo "################################################"
echo ${DIR}
echo "################################################"

BUILDBASE=${DIR}/build
DISTDIR=${DIR}/dist
CACHEDIR=./build/download-cache
BUILDDIR=${BUILDBASE}/Oasys2

PIP_INDEX_ARGS=()
PIP_ARGS=(oasys2)

PYTHON_VERSION=${PYTHON_VERSION:-"3.13.9"}
PYTHON_NUPKG="${CACHEDIR}/python-${PYTHON_VERSION}.nupkg"

# Suppress MSYS2 auto unix -> win path expansion
export MSYS2_ARG_CONV_EXCL="*"

while [[ "${1:0:1}" = "-" ]]; do
    case $1 in
        -b|--build-base)
            BUILDBASE=${2:?}; shift 2;;
        --build-base=*)
            BUILDBASE=${1#*=}; shift 1;;
        -d|--dist-dir)
            DISTDIR=${2:?}; shift 2;;
        --dist-dir=*)
            DISTDIR=${1#*=}; shift 1;;
        --cache-dir)
            CACHEDIR=${2:?}; shift 2;;
        --cache-dir=*)
            CACHEDIR=${1#*=}; shift 1;;
        --python-version)
            PYTHON_VERSION=${2:?}; shift 2;;
        --python-version=*)
            PYTHON_VERSION=${1#*=}; shift 1;;
        -f|--find-links)
            PIP_INDEX_ARGS+=(--find-links "${2:?}"); shift 2;;
        --find-links=*)
            PIP_INDEX_ARGS+=(--find-links "${1#*=}"); shift 1;;
        --extra-index-url)
            PIP_INDEX_ARGS+=(--extra-index-url "${2:?}"); shift 2;;
        --extra-index-url=*)
            PIP_INDEX_ARGS+=(--extra-index-url "${1#*=}"); shift 1;;
        --no-index)
            PIP_INDEX_ARGS+=( --no-index ); shift 1;;
        --pip-arg)
            PIP_ARGS+=( "${2:?}" ); shift 2;;
        --pip-arg=*)
            PIP_ARGS+=( "${1#*=}" ); shift 1;;
        -h|--help)
            usage; exit 0;;
        -*)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
     esac
done

function download {
  local url=${1:?}
  local dest=${2:?}
  local tmpname=""
  mkdir -p $(dirname "${dest}")
    if [[ ! -f "${dest}" ]]; then
        tmpname=$(mktemp "${dest}.XXXXX")
        if curl -fSL -o "${tmpname}" "${url}"; then
            mv "${tmpname}" "${dest}"
        else
            return $?
        fi
    fi
}


download https://www.nuget.org/api/v2/package/python/${PYTHON_VERSION} "${PYTHON_NUPKG}"

if [[ -e "${BUILDDIR}" ]]; then
  rm -r "${BUILDDIR}"
fi

7z x '-i!tools' -y -o"${BUILDBASE}/tmp" "${PYTHON_NUPKG}"
mkdir -p $(dirname "${BUILDDIR}")
mv "${BUILDBASE}/tmp/tools" "${BUILDDIR}"

PYTHON="${BUILDDIR}/python.exe"

"${PYTHON}" -m ensurepip
"${PYTHON}" -m pip install --no-warn-script-location "pip==25.3.*" wheel
"${PYTHON}" -m pip install "${PIP_INDEX_ARGS[@]}" --no-warn-script-location "${PIP_ARGS[@]}"

mkdir -p "${BUILDDIR}/etc"
cp "${DIR}/oasysrc.conf" "${BUILDDIR}/etc/oasysrc.conf"

BUILDDIR_WIN="$(cygpath -w "${BUILDDIR}")"
BUILDBASE_WIN="$(cygpath -w "${BUILDBASE}")"

"${PYTHON}" -m pip install --no-warn-script-location pywin32 

"${PYTHON}" "${DIR}/create_shortcut.py" \
   --target '%SystemRoot%\\system32\\cmd.exe' \
   --arguments '"/C python.exe -m oasys2.canvas"' \
   --working-directory "" \
   --window-style Minimized \
   --shortcut "${BUILDDIR_WIN}\Oasys2.lnk"

"${PYTHON}" "${DIR}/create_shortcut.py" \
   --target '%SystemRoot%\\system32\\cmd.exe' \
   --arguments '"/C Oasys2\python.exe -m oasys2.canvas"' \
   --working-directory "" \
   --window-style Minimized \
   --shortcut "${BUILDBASE_WIN}\Oasys2.lnk"

cp "${FULL_DIR}/Oasys2.ico" "${BUILDDIR}/Oasys2.ico"

pushd ${BUILDBASE}

echo [global]        > Oasys2/pip.ini
echo prefer-binary=1 >> Oasys2/pip.ini

7z a -tzip -mx=9 temp.zip Oasys2 Oasys2.lnk -xr!*.pyc -xr!*.pyo -xr!*/__pycache__/*

popd

mv -f "${BUILDBASE}/temp.zip" "${DISTDIR}/Oasys${VERSION}.zip"
