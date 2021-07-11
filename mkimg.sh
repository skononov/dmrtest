#!/bin/bash

if [ $# -gt 0 ]; then
  if [ ${1:${#1}-4} = '.img' -a -s $1 ]; then
    imgfn=$1
  elif [ -b $1 ]; then
    devfn=$1
  else
    echo "$1: Illegal argument. Must be an existing image or device file."
    exit -1
  fi
else
  echo -e "Usage: $0 devfn|imgfn [img2fn]\nCreating truncated and zipped image file from a given device or image and write to an image file."
  exit 0
fi

if [ $# -gt 1 ]; then
  if [ ${2:${#2}-4} = '.img' ]; then
    img2fn=$2
  else
    echo "$2: Second argument must be an image filename."
    exit -1
  fi
fi

if [ -n "$devfn" ] &&  [ ! -b "$devfn" ]; then
  echo "Block device $devfn does not exist"
  exit 1
fi

if [ -n "$imgfn" ] && [ ! -r $imgfn ]; then
  echo "File $imgfn does not exist"
  exit 1
fi

if [ -n "$img2fn" -a "$img2fn" != "$imgfn" -a -s "$img2fn" ]; then
  R=x
  while [ "$R" != 'y' -a "$R" != 'n' -a "$R" != 'yes' -a "$R" != 'no' ]; do
    read -p "Rewrite existing image file '$img2fn'? [y/n] " R
    R="${R,}"
  done
  if [ "${R:0:1}" != 'y' ]; then
    echo "Exiting"
    exit 0
  fi
elif [ -z "$img2fn" ]; then
  for ((i=1; ; i++)); do
    img2fn="rpi${i}.img"
    [ ! -f $img2fn ] && break
  done
fi

if [ -n "$devfn" ]; then
  echo "Copying block device $devfn to image file $img2fn with 'dd'..."
  dd if=$devfn of=$img2fn status=progress || exit 1
elif [ -n "$imgfn" -a "$imgfn" != "$img2fn" ]; then
  echo "Copying image file $imgfn to $img2fn..."
  cp -pv $imgfn $img2fn || exit 1
fi

chown skononov:skononov $img2fn

loopfn=$(losetup -f) || exit 1

echo -e "\nConnect loop device '$loopfn' to the image '$img2fn'"
losetup $loopfn $img2fn || exit 1

trap "echo Disconnecting loop device $loopfn; losetup -d $loopfn" EXIT

partprobe -s $loopfn || exit 1

echo -e "\nChecking and recovering filesystem at '${loopfn}p2' with 'e2fsck'"
e2fsck -f -y -C 0 "${loopfn}p2" || exit 1

declare -i psizeblk=$(resize2fs -P "${loopfn}p2" 2>/dev/null | sed -nr 's/^.*: ([0-9]+)/\1/p')

echo -e "\nResizing filesystem at '${loopfn}p2' to $psizeblk 4K-blocks with 'resize2fs'"
resize2fs -p "${loopfn}p2" $psizeblk || exit 1

declare -i psizesec=$[(psizeblk/256+1)*1024*2] # 512b-sectors rounded to MiB

#parted does not work as expected, changes are not saved?
#echo -e "\nResizing partition at ${loopfn}p2 to $psizesec 512b-sectors with 'parted'"
#parted "${loopfn}p2" unit s resizepart 1 $[psizesec-1] || exit 1

echo -e "\nResizing partition at ${loopfn}p2 to $psizesec 512b-sectors with 'sfdisk'"
echo -e ", $psizesec, L" | sfdisk -N 2 "${loopfn}" || exit 1

partprobe -s $loopfn || exit 1

echo -e "\nChecking and recovering filesystems at '${loopfn}' with 'e2fsck'"
fsck.ext4 -f -y -C 0 "${loopfn}p2" || exit 1
fsck.fat -a -v "${loopfn}p1" || exit 1

declare -i devtotsizebytes=$(parted -m $loopfn unit b print | sed -rn 's/^2:[0-9]+B:([0-9]+)B:.*$/\1/p' )+1

trap "" EXIT
echo "Disconnecting loop device '$loopfn'"
losetup -d $loopfn

echo -e "\nTruncating '$img2fn' to $devtotsizebytes bytes with 'truncate'"
truncate --size=$devtotsizebytes $img2fn || exit 1

zipfn=$(echo $img2fn | tr . _).zip
echo -e "\nZipping image file '$img2fn' to '$zipfn'"
zip -v $zipfn $img2fn

chown skononov.skononov $zipfn

