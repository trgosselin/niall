import os
from os.path import exists
import glob

rootdir = "/mnt/cluster/data/SRPBS_multidisorder_MRI/traveling_subjects/SRPBTravel/"
t1fns = glob.glob( rootdir + "*/anat/*.nii.gz" )
import sys
fileindex = 0
if len( sys.argv ) > 1:
    fileindex = int(sys.argv[1])
t1fn = t1fns[ fileindex ]
import re
mysubbed = re.sub('anat', 'T1wH', t1fn )
mysubbed = re.sub('traveling_subjects/SRPBTravel','traveling_subjects_repro_study',mysubbed)
mysubbed = re.sub('.nii.gz','',mysubbed)
newprefix = re.sub('_T1w','_T1wH',mysubbed)
mysubbedsplit = newprefix.split("/")
# define the directories and create them
newoutdir = ''
keyindex = len(mysubbedsplit) - 1 # change for each case
for k in range(keyindex):
    newoutdir = newoutdir + '/' + mysubbedsplit[k]
newoutdir=newoutdir+'/'
os.makedirs( newoutdir, exist_ok=True  )

print( "RUN " +  newprefix  + " " )
import ants
import antspynet
import antspymm
import tensorflow as tf
import tensorflow.keras.backend as K
K.set_floatx("float32")
import antspyt1w
import superiq
t1 = ants.image_read( t1fn )
bxtsylelist = ['v0','v0']
for bxtstyle in bxtsylelist:
    srfnout = newprefix + "_" + bxtstyle
    print("begin: " + srfnout  )
    t1bxt = antspyt1w.brain_extraction( t1, method=bxtstyle )
    t1 = t1 * t1bxt
    t1 = antspyt1w.preprocess_intensity( t1, t1bxt )
    tfn = antspyt1w.get_data('T_template0', target_extension='.nii.gz' )
    tlrfn = antspyt1w.get_data('T_template0_LR', target_extension='.nii.gz' )
    templatea = ants.image_read( tfn )
    templatea = ( templatea * antspynet.brain_extraction( templatea, 't1' ) ).iMath( "Normalize" )
    templatealr = ants.image_read( tlrfn )
    t1crop = ants.crop_image( t1, ants.iMath(  t1bxt, "MD", 6 ) )
    t1crop = ants.iMath( t1crop, "TruncateIntensity", 1e-4, 0.999 ).iMath( "Normalize" )
    ants.image_write( t1crop, newprefix + "brain_n4_dnz.nii.gz" )
    print( "t1crop" )
    print( t1crop )
    mylr = antspyt1w.label_hemispheres( t1crop, templatea, templatealr )
    print("second is SR")
    mdlfn = "/home/ubuntu/models/SEGSR_32_ANINN222_3.h5"
    mdl = tf.keras.models.load_model( mdlfn )
    mysr = superiq.super_resolution_segmentation_per_label(
            t1crop, mylr, [2,2,2], mdl, [1,2], dilation_amount=0, probability_images=None,
            probability_labels=None, max_lab_plus_one=False, verbose=True )
    t1 = mysr['super_resolution']
    t1bxt = ants.resample_image_to_target( t1bxt, t1, interp_type='nearestNeighbor' )
    ants.image_write( t1, newprefix + ".nii.gz" )
    ants.image_write( t1bxt, newprefix + "brain_extraction.nii.gz" )
    print("begin hier: " + newprefix )
    t1h = antspyt1w.hierarchical( t1, output_prefix=srfnout, imgbxt=t1bxt, cit168=True )
    antspyt1w.write_hierarchical( t1h, output_prefix=newprefix )
    print("complete: " + srfnout )
