#!/usr/bin/env python3
# coding: utf-8

import os, re, contextlib, glob
# confusingly, the package is called 'Pillow' but
# the module name is still PIL (Python Imaging Library)
from PIL import Image, ImageMath
from argparse import ArgumentParser

@contextlib.contextmanager
def working_directory(path):
    """
    A context manager that changes the working directory to the given
    path and reverts to its previous value on exit.
    """
    prev_wd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_wd)

def filter_size(filesdir: str,min_size: int):
    """
    Find files less than a given size and return their paths
    (to get all the image sizes, simply pass a huge `min_size`)
    Args:
        filesdir: directory where we look for files
        min_size: cutoff size (in bytes); any image smaller is returned
    Return: List of (name,size) tuples of images
    """
    with working_directory(filesdir):
        ff = glob.glob('*.png')
        fs = [os.path.getsize(f) for f in ff]
    return [(f,sz) for f,sz in zip(ff,fs) if sz <= min_size]

def filter_entropy(filesdir: str,min_e: float):
    """
    calculate the entropy and filter files lower than a given
    threshold
    Args:
        filesdir: directory where we look for files
        min_size: cutoff size; images with smaller entropy are returned
    Return: List of (name,size) tuples of images
    """
    
    def img_entropy(imgpath):
        with Image.open(imgpath,'r') as img:
            return img.entropy()

    with working_directory(filesdir):
        ff = glob.glob('*.png')
        ee = [img_entropy(e) for e in ff]
    return [(f,e) for f,e in zip(ff,ee) if e <= min_e]

def apply_filter(filesdir,imgs,outdir = None):
    """
    Having used some filters to identify 'bad' images, move them into
    `outdir`; if that is `None`, then simply deletes `imgs`.
    Args:
        filesdir: directory where the images are
        imgs: images we want to move or delete
        outdir: destination of images (`None` to delete them)
    """
    with working_directory(filesdir):
        imgs = [e for e in imgs if os.path.exists(e)]
        print(f"Identified {len(imgs)} files to filter")
        if outdir is None:
            [os.remove(img) for img in imgs]
        else:
            os.makedirs(outdir,exist_ok=True)
            for img in imgs:
                os.rename(img,os.path.join(outdir,os.path.basename(img)))


if __name__ == '__main__':

    ap = ArgumentParser(
        description = "filter low-quality or empty files"
    )
    ap.add_argument(
        "--dir","-d",required = True,type = str,
        help = "The directory where the images reside"
    )
    ap.add_argument(
        "--min_size","-m",required = True,type = int,
        help = "The file size in bytes (anything smaller is (re)moved)"
    )
    ap.add_argument(
        "--min_entropy","-e",required = False,
        type = float,nargs = '?',default = None,
        help = "(optional) - the min. entropy to keep the image"
    )
    ap.add_argument(
        "--outdir","-o",required = False,
        type = str,nargs = '?',default = None,
        help = "Destination directory for failed images (they're deleted if this option is not specified)"
    )    
    argz = vars(ap.parse_args())
    
    wkdir = argz['dir']
    odir = argz['outdir']
    filter1 = filter_size(wkdir,argz['min_size'])
    if argz['min_entropy']:
        filter2 = filter_entropy(wkdir,argz['min_entropy'])
        fi2 = [e[0] for e in filter2]
        filter1 = [pair for pair in filter1 if pair[0] in fi2]

    targets = [e[0] for e in filter1]
    apply_filter(wkdir,targets,odir)
    if False:
        # example usage:
        img_dir = "/mnt/c/Users/skm/Dropbox/AgileBeat/pipeline-1"
        ff1 = filter_size(img_dir,1250)
        ff2 = filter_entropy(img_dir,25)
        # we could combine these filters in whatever way is useful
        # but they are pretty highly correlated, since file size is basically
        # a proxy for how compressible the image is...aka entropy.
        small_imgs = [e[0] for e in ff1]
        apply_filter(img_dir,small_imgs,'graveyard')
    