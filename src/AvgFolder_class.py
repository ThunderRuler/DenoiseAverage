# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 06:44:03 2017

@author: Mauro
"""

# This module deals with the Average

# Define Imports

# pyplot
import matplotlib.pyplot as plt

# numpy import
import numpy as np

# py imports
from os.path import isdir, isfile, join, splitext, split
from os import listdir, mkdir
from copy import deepcopy
import logging as lg
import pickle

# My imports
from MyImage_class import MyImage
from ImageFFT_class import ImgFFT

#==============================================================================
# Exceptions
#==============================================================================

class TemplateTypeError(Exception):
   def __init__(self, value):
       self.value = value
   def __str__(self):
       return "Wrong template type: " + repr(self.value)

#==============================================================================
# Class Average Folder
#==============================================================================

class AvgFolder(object):
    
    # Initialization functions
    def __init__(self, path):
        # define the main path
        self.path = path
        
        # folder environment variable
        self.names = []
        self.avgpath = ""
        self.subfolders = {}
        
        # create the folder environment
        try:
            self.makeavgdir()
        except FileNotFoundError as e:
            print("Folder not found")
        except:
            print("WTF")
            
        # create log file in the avg folder
        lg.basicConfig(filename=join(self.avgpath,'example.log'),level=lg.INFO)
        
        # initialize variables
        self.imgs = []
        self.template = MyImage()
        self.templateft = None
        self.angles_list = []
        self.templaterotsft = []
               
        self.algimgs = []
        self.corrs = []
        self.shifts = []
        
        self.avg = MyImage()
        
    
    def gather_pictures(self):
        # for now gather all the files, next check for picture extensions
        p = self.path
        self.names = [f for f in listdir(p) if isfile(join(p, f))]

        for imgname in self.names:
            imagepath = join(self.path, imgname)
            img = MyImage()
            img.read_from_file(imagepath)
            self.imgs.append(img)
            lg.info("Image: {0} imported successfully".format(imagepath))

    def makeavgdir(self):
        # create a folder average into the dataset path
        # avg
        #  |- processed_images
        #  |- aligned_images
        #  |- correlation_images
        #  |- results
        self.avgpath = join(self.path, "avg")
        if not isdir(self.avgpath):
            mkdir(self.avgpath)
        
        subfolders = ["processed_images", "aligned_images", 
                      "correlation_images", "results"]
        for folder in subfolders:
            self.subfolders[folder] = join(self.avgpath, folder)
            if not isdir(self.subfolders[folder]):
                mkdir(self.subfolders[folder])    

    
    # image operations
    def c2gscale(self):
        for img in self.imgs:
            img.convert2grayscale()
        lg.info("dataset converted to grayscale")
    
    def squareit(self):
        for img in self.imgs:
            img.squareit()
        lg.info("dataset squared")
 
    def transpose(self):
        for img in self.imgs:
            img.transpose()
        lg.info("dataset transposed")
        
    def normalize(self):
        for img in self.imgs:
            img.normalize()    
        lg.info("dataset normalized")
    
    def binning(self, n = 1):
        for img in self.imgs:
            img.binning(n)
        lg.info("dataset binned {0} times".format(n))
    
    # template handling
    def generate_template(self, option, rot_precision = None):
        if type(option) is str:
            if option == "UseFirstImage":
                self.template = self.imgs[0]
                self.templateft = ImgFFT(self.template)
                self.templateft.ft()
            elif option == "Average":
                self.average(False)
                self.template = self.avg
                self.templateft = ImgFFT(self.template)
                self.templateft.ft()
            else:
                raise TemplateTypeError(option)
        elif type(option) == MyImage:
            self.template = option
            self.templateft = ImgFFT(self.template)
            self.templateft.ft()
        else:
           raise TemplateTypeError(type(option))
        lg.info("template created: {0}".format(option))
    
        if type(rot_precision) == tuple:
            
            print("Creating rotation references")
            
            # rot_precision format = (from, to, precision)
            frm = rot_precision[0]
            to = rot_precision[1]
            prec = rot_precision[2]
            self.angles_list = np.arange(frm, to, prec)
            
            print("From", frm, "to", to, "precision", prec)
            print("Total:", len(self.angles_list), "angles")
            
            for angle in self.angles_list:
                print("creating angle: ", angle)
                rot = deepcopy(self.template)
                rot.rotate(angle)
                
                rotft = ImgFFT(rot)
                rotft.ft()
                
                self.templaterotsft.append(rotft)
    

    
    def align_images(self, debug = False):
        c = 0
        for image in self.imgs:
            
            # generate the fourier transform of the image
            imgft = ImgFFT(image)
            imgft.ft()
            
            # calculate the rotations
            smax = 0
            idxmax = 0
            for idx, temp in enumerate(self.templaterotsft):
                corr = temp.correlate(imgft)
                s, dx, dy = corr.find_peak(1)
                
                if s > smax:
                    smax = s
                    idxmax = idx
            
            print("angle found",self.angles_list[idxmax] )
            
            rotalgimage = deepcopy(image)
            rotalgimage.rotate(-self.angles_list[idxmax])    
            
            # calculate the shifts
            rotalgimageft = ImgFFT(rotalgimage)
            rotalgimageft.ft()
            
            corr = rotalgimageft.correlate(self.templateft)
            self.corrs.append(corr)
            
            dx, dy = corr.find_translation(1)
            self.shifts.append((dx,dy))
            
            print("shifts:", dx, dy)
            
            rotalgimage.move(dx, dy) 
            self.algimgs.append(rotalgimage)
            
            if debug:
                print("Correlate image:", c)            
            lg.info("correlated image n: " + str(c))
            
            c += 1
    
    def average(self, aligned = True):
        if aligned:
            dataset = self.algimgs
        else:
            dataset = self.imgs
        s = MyImage(np.zeros(dataset[0].data.shape))
        for picture in dataset:
            s += picture
        
        
        self.avg = s / len(dataset)
    
    # I/O methods
    def save_template(self):
        self.template.save(join(self.avgpath, "template.png"))
            
    def load_template(self, filepathname):
        self.template.read_from_file(filepathname)
    
    def save_imgs(self):
        for i, img in enumerate(self.imgs):
            filename, ext = splitext(self.names[i])
            img.save(join(self.subfolders["processed_images"], "proc_" + filename + ".png"))
        lg.info("processed dataset saved, images {0}".format(i))
    
    def laod_imgs(self):
        lg.info("Loading processed images")
        p = self.subfolders["processed_images"]
        names = [f for f in listdir(p) if isfile(join(p, f))] 
        
        self.imgs = []
        for name in names:
            img = MyImage()
            img.read_from_file(name)
            self.imgs.append(img)
            lg.info("Image: {0} imported successfully".format(name))
            
    
    def save_algimgs(self):
        for i, algimg in enumerate(self.algimgs):
            filename, ext = splitext(self.names[i])
            algimg.save(join(self.subfolders["aligned_images"], ("alg_" + filename + ".png" )))
        lg.info("aligned dataset saved, images {0}".format(i))
    
    def laod_algimgs(self):
        lg.info("Loading aligned images")  
        p = self.subfolders["aligned_images"]
        names = [f for f in listdir(p) if isfile(join(p, f))] 
        
        self.imgs = []
        for name in names:
            img = MyImage()
            img.read_from_file(name)
            self.imgs.append(img)
            lg.info("Image: {0} imported successfully".format(name))    
    
    def save_corrs(self):
        for i, corr in enumerate(self.corrs):
            filename, ext = splitext(self.names[i])
            corr.save(join(self.subfolders["correlation_images"], ("corr_" + filename + ".png" )))
        lg.info("correlations dataset saved, images {0}".format(i))

    def laod_corrs(self):
        lg.info("Loading correlation images")  
        p = self.subfolders["correlation_images"]
        names = [f for f in listdir(p) if isfile(join(p, f))] 
        
        self.imgs = []
        for name in names:
            img = MyImage()
            img.read_from_file(name)
            self.imgs.append(img)
            lg.info("Image: {0} imported successfully".format(name))    
    
    def save_avg(self):
        self.avg.save(join(self.subfolders["results"], "avg.png"))
    
    def save_shifts(self):
        with open(join(self.subfolders["results"], "shifts_log.txt"), "w") as f:
            for shift in self.shifts:
                f.write("{0[0]:d} | {0[1]:d}\n".format(shift))
        lg.info("Shifts saved")

    def load_shifts(self):
        with open(join(self.subfolders["results"], "shifts_log.txt")) as f:
            lines = f.readlines()
        
        self.shifts = []
        for line in lines:
            data = line.split(' - ')
            data = [int(d.strip()) for d in data]
            print (data)
            self.shifts.append(data)

# TO DO
# - process function with arguments
# - check if already calculated 


#==============================================================================
# Class Average Folder Save Memory
#==============================================================================

def get_pathname(path):
    ''' Little function to split the path in path, name, extension'''
    path, nameext = split(path)
    name, ext = splitext(nameext)
    return path, name, ext

class BaseArray:
    
    def __init__(self, path):
        if type(path) == list:
            self.paths = path
        elif type(path) == str:
            self.generate_paths(path)
        elif type(path) == tuple:
            self.generate_paths_from_names(path[0], path[1], path[2])
        self.i = 0
        self.n = len(self.paths)

    def generate_paths_from_names(self, path, basename, i):
        npath, name, ext = get_pathname(basename)
        
        self.paths = []
        for n in range(i):
            respath = join(path, name + "_" + str(n) + ext)
            self.paths.append(respath)
    
    def __iter__(self):
        return self

    def __next__(self):
        if self.i < self.n:
            img = self.get_image(self.i)
            self.i += 1
            return img
        else:
            self.i = 0
            raise StopIteration()  
    
    def __getitem__(self, i):
        return self.get_image(i)



class ImageArray(BaseArray):

    def __init__(self, path):
        super(ImageArray, self).__init__(path)
    
    def generate_paths(self, path):
        # gather files in folder
        names = [get_pathname(join(path, f)) for f in listdir(path) if isfile(join(path, f))] 
        
        self.paths = []
        for n in names:
            if n[2] in ['.jpg', '.png']:
                self.paths.append(join(n[0], n[1] + n[2]))

    def get_image(self, i):
        path = self.paths[i]
        image = MyImage(path)
        return image
    
    def set_image(self, i):
        print("ERROR cant save with this class")



class NpyImageArray(BaseArray):
    
    def __init__(self, path):
        super(NpyImageArray, self).__init__(path)
    
        
    def generate_paths(self, path):
        # gather files in folder
        names = [get_pathname(join(path, f)) for f in listdir(path) if isfile(join(path, f))] 
        
        self.paths = []
        for n in names:
            if n[2] in ['.pickle']:
                self.paths.append(join(n[0], n[1] + n[2]))

    def get_image(self, i):
        with open(self.paths[i], 'rb') as f:
            data = np.load(f)
        return MyImage(data)
    
    def set_image(self, i, image):
        with open(self.paths[i], 'wb') as f:
            np.save(f, image.data)

class NpyFTArray(BaseArray):
    
    def __init__(self, path):
        super(NpyFTArray, self).__init__(path)
        
    def generate_paths(self, path):
        # gather files in folder
        names = [get_pathname(join(path, f)) for f in listdir(path) if isfile(join(path, f))] 
        self.paths = []
        for n in names:
            if n[2] in ['.npy']:
                self.paths.append(join(n[0], n[1] + n[2]))

    def get_image(self, i):
        with open(self.paths[i], 'rb') as f:
            imgfft = np.load(f)
            ft = ImgFFT(MyImage())
            ft.imgfft = imgfft
        return ft
    
    def set_image(self, i, image):
        with open(self.paths[i], 'wb') as f:
            np.save(f, image.imgfft)

class AvgFolderMem(object):
    
    # Initialization functions
    def __init__(self, path):
        # define the main path
        self.path = path
        
        # folder environment variable
        self.names = []
        self.avgpath = ""
        self.subfolders = {}
        
        # create the folder environment
        try:
            self.makeavgdir()
        except FileNotFoundError as e:
            print("Folder not found")
        except:
            print("WTF")
            
        # create log file in the avg folder
        lg.basicConfig(filename=join(self.avgpath,'example.log'),level=lg.INFO)
        
        # pictures
        self.init_imgs = ImageArray(self.path)
        self.imgs = NpyImageArray((self.subfolders["processed_images"], "proc_imgs.npy", len(self.init_imgs.paths)))
        
        
        
        # initialize variables
        self.template = MyImage()
        self.templateft = None
        self.angles_list = []
        
        self.templaterotsft = None
        
        folder = self.subfolders["aligned_images"]
        bname = "algimage.npy"
        q = self.imgs.n               
        self.algimgs = NpyImageArray((folder, bname, q))
        
        folder = self.subfolders["correlation_images"]
        bname = "correlation.npy"
        q = self.imgs.n
        self.corrs = NpyImageArray((folder, bname, q))
        
        self.shifts = []
        
        self.avg = MyImage()
    


    def makeavgdir(self):
        # create a folder average into the dataset path
        # avg
        #  |- processed_images
        #  |- aligned_images
        #  |- correlation_images
        #  |- results
        #  |- template_rot
        self.avgpath = join(self.path, "avg")
        if not isdir(self.avgpath):
            mkdir(self.avgpath)
        
        subfolders = ["processed_images", "aligned_images", 
                      "correlation_images", "results",
                      "template_rot"]
        for folder in subfolders:
            self.subfolders[folder] = join(self.avgpath, folder)
            if not isdir(self.subfolders[folder]):
                mkdir(self.subfolders[folder])    
    
    def gather_pictures(self):
        for i, image in enumerate(self.init_imgs):
            self.imgs.set_image(i, image)
    
    # image operations
    def c2gscale(self):
        for i, img in enumerate(self.imgs):
            img.convert2grayscale()
            self.imgs.set_image(i,img)
        lg.info("dataset converted to grayscale")
    
    def squareit(self):
        for i, img in enumerate(self.imgs):          
            img.squareit()
            self.imgs.set_image(i,img)
        lg.info("dataset squared")
 
    def transpose(self):
        for i, img in enumerate(self.imgs):
            img.transpose()
            self.imgs.set_image(i,img)
        lg.info("dataset transposed")
        
    def normalize(self):
        for i, img in enumerate(self.imgs):
            img.normalize()
            self.imgs.set_image(i,img)
        lg.info("dataset normalized")
    
    def binning(self, n = 1):
        for i, img in enumerate(self.imgs):
            img.binning(n)
            self.imgs.set_image(i,img)
        lg.info("dataset binned {0} times".format(n))
    
    # template handling
    def generate_template(self, option, rot_precision = None):
        if type(option) is str:
            if option == "UseFirstImage":
                self.template = self.imgs.get_image(0)
                self.templateft = ImgFFT(self.template)
                self.templateft.ft()
            elif option == "Average":
                self.average(False)
                self.template = self.avg
                self.templateft = ImgFFT(self.template)
                self.templateft.ft()
            else:
                raise TemplateTypeError(option)
        elif type(option) == MyImage:
            self.template = option
            self.templateft = ImgFFT(self.template)
            self.templateft.ft()
        else:
           raise TemplateTypeError(type(option))
        lg.info("template created: {0}".format(option))
        
        
        if type(rot_precision) == tuple:
            
            print("Creating rotation references")
            
            # rot_precision format = (from, to, precision)
            frm = rot_precision[0]
            to = rot_precision[1]
            prec = rot_precision[2]
            self.angles_list = np.arange(frm, to, prec)
            
            print("From", frm, "to", to, "precision", prec)
            print("Total:", len(self.angles_list), "angles")
            self.templaterotsft = NpyFTArray((self.subfolders["template_rot"],
                                              "template_rot_ft.npy", 
                                              len(self.angles_list)
                                              ))
            for i, angle in enumerate(self.angles_list):
                print("creating angle: ", angle)
                rot = deepcopy(self.template)
                rot.rotate(angle)
                
                rotft = ImgFFT(rot)
                rotft.ft()
                
                self.templaterotsft.set_image(i, rotft)
    

    
    def align_images(self, debug = False):
        c = 0
        
        for image in self.imgs:
            
            # generate the fourier transform of the image
            imgft = ImgFFT(image)
            imgft.ft()
            
            # calculate the rotations
            smax = 0
            idxmax = 0
            for idx, temp in enumerate(self.templaterotsft):
                corr = temp.correlate(imgft)
                s, dx, dy = corr.find_peak(1)
                
                if s > smax:
                    smax = s
                    idxmax = idx
            
            angle = float(self.angles_list[idxmax])
            
            print("angle found", angle)
            
            rotalgimage = deepcopy(image)
            rotalgimage.rotate(-angle)    
            
            # calculate the shifts
            rotalgimageft = ImgFFT(rotalgimage)
            rotalgimageft.ft()
            
            corr = rotalgimageft.correlate(self.templateft)
            self.corrs.set_image(c, corr)
            
            dx, dy = corr.find_translation(1)
            self.shifts.append((dx, dy, angle))
            
            print("shifts:", dx, dy)
            
            rotalgimage.move(dx, dy) 
            
            self.algimgs.set_image(c, rotalgimage)
            
            if debug:
                print("Correlated image:", c)    
                
            lg.info("correlated image n: " + str(c))
            
            c += 1
    
    def average(self, aligned = True):
#        self.imgs.i = 0
#        self.algimgs.i = 0
        
        if aligned:
            dataset = self.algimgs
        else:
            dataset = self.imgs
        s = MyImage(np.zeros(dataset[0].data.shape))
        for picture in dataset:
            s += picture
        
        
        self.avg = s / dataset.n
    
    # I/O methods
    def save_template(self):
        self.template.save(join(self.avgpath, "template.png"))
            
    def load_template(self, filepathname):
        self.template.read_from_file(filepathname)            
    
    def save_avg(self):
        self.avg.save(join(self.subfolders["results"], "avg.png"))
    
    def save_shifts(self):
        with open(join(self.subfolders["results"], "shifts_log.txt"), "w") as f:
            for shift in self.shifts:
                f.write("{0[0]:d} | {0[1]:d} | {0[2]:.3f}\n".format(shift))
        lg.info("Shifts saved")

    def load_shifts(self):
        with open(join(self.subfolders["results"], "shifts_log.txt")) as f:
            lines = f.readlines()
        
        self.shifts = []
        for line in lines:
            sdata = line.split(' | ')
            sdata = [d.strip() for d in sdata]
            data = [int(sdata[0]), int(sdata[1]), float(sdata[2])]
            print (data)
            self.shifts.append(data)

class AnalyzeShifts:
    
    def __init__(self, pathtolog):

        
        with open(pathtolog, "r") as f:
            lines = f.readlines
        
        # process the lines
        self.shifts = []
        for line in lines:
            self.shifts.append(self.read_shifts(line))
        
        self.shiftsx = [data[0] for data in self.shifts]
        self.shiftsy = [data[1] for data in self.shifts]
        self.angles  = [data[2] for data in self.shifts]        
    
    def read_shifts(self, line):
        sdata = line.split(' | ')
        sdata = [d.strip() for d in sdata]
        data = [int(sdata[0]), int(sdata[1]), float(sdata[2])]
        return data      
    
    def plot_xy(self):
        import matplotlib.pyplot as plt
        plt.scatter(self.shiftsx, self.shiftsy)
        plt.show()
    
    def plot_angles(self):
        x = np.cos(self.angles)
        y = np.sin(self.angles)
        plt.scatter(x, y)
        plt.show()
        
if __name__ == "__main__":

 
    
    testdatasetpath = "../../../silentcam/testdataset/"
    template_folder = join(testdatasetpath, "template_folder")

#    if not isdir(testdatasetpath):
#        mkdir(testdatasetpath)  
#    
#    logpathdir = join(testdatasetpath, "tlog")
#    if not isdir(logpathdir):
#        mkdir(logpathdir)    
#    
#    # create a test dataset:
#    mypicname = "../../../Lenna.png"
#    mypic = MyImage()
#    mypic.read_from_file(mypicname)
#    mypic.squareit()
#    mypic.convert2grayscale()
#    mypic.binning(2)
#    mypic.normalize()
#    
#    
#    if not isdir(template_folder):
#        mkdir(template_folder)
#        
#    mypic.save(join(template_folder, "template.png"))
#    
#    mypic.show_image()
#    plt.show()
#    
#
#
#    print("------------------------------")
#    print("creating dataset")
#    print("------------------------------")   
#
#    np.random.seed(5)
#    datasetangles = []
#    datasetshifts = []
#    
#    datatrans = []
#    
#
#    
#    
#    with open(join(logpathdir, "mytransformations.log"), 'w') as f:
#        for i in range(5):
#            image = deepcopy(mypic)
#           
#            anglefirst = False if np.random.randint(0,2) == 0 else True
#            angle = np.random.randint(-10, 10) / float(10)
#            dx = np.random.randint(-50, 50)
#            dy = np.random.randint(-50, 50)
#            
#            f.write("{0} {1} {2} {3}\n".format(anglefirst, angle, dx, dy))
#            
#            
#            datatrans.append((anglefirst, angle, dx, dy))
#            
#            if anglefirst:
#                datasetangles.append(angle)
#                image.rotate(angle)
#    
#                datasetshifts.append((dx,dy))
#                image.move(dx, dy)
#            else:
#                datasetshifts.append((dx,dy))
#                image.move(dx, dy) 
#    
#                datasetangles.append(angle)
#                image.rotate(angle)
#            
#            print(datatrans[i])
#               
#            image.show_image()
#            plt.show()
#            
#            image.save(join(testdatasetpath, "pic_" + str(i) + ".png"))                                         


    print("------------------------------")
    print("Loading dataset")
    print("------------------------------")  

    mypath = "../../../silentcam/dataset34/"
    avg = AvgFolderMem(mypath)
    avg.gather_pictures()
    avg.c2gscale()
    avg.squareit()
    avg.binning(0)
    avg.transpose()
    avg.normalize()


    print("------------------------------")
    print("Generating template")
    print("------------------------------")  
    
#    custom_template = MyImage()
#    custom_template.read_from_file(join(template_folder, "template.png"))
#    custom_template.convert2grayscale()

    avg.generate_template("UseFirstImage", (-1, 1, 0.1))
    avg.save_template()
    
    avg.template.show_image()
    plt.show()  
    
    avg.template.inspect()    
 
  
    
    correlate = True
    if correlate:
        # aling dataset
        print("------------------------------")
        print("Alignment")
        print("------------------------------")
        
        avg.align_images()
        avg.save_shifts()
    
        print("------------------------------")
        print("Average")
        print("------------------------------")          
        avg.average()
        avg.save_avg()
        
        avg.avg.inspect()
        
        avg.avg.show_image()
        plt.show()   
    
#    mypath = "../../silentcam/dataset25/"
#    avg = AvgFolder(mypath)
#    avg.gather_pictures()
#    avg.c2gscale()
#    avg.squareit()
#    avg.binning(0)    
#    avg.transpose()
#    avg.normalize() 
#    
#    avg.save_imgs()
#
#        
#    avg.generate_template("UseFirstImage")
#    avg.save_template()
#    
#    avg.template.show_image()
#    plt.show()  
#    
#    avg.template.inspect()
#    
#    correlate = True
#    if correlate:
#        # aling dataset
#        avg.align_images()
#        avg.save_algimgs()
#        avg.save_corrs()
#        avg.save_shifts()
#        
#        avg.average()
#        avg.save_avg()
#        avg.avg.show_image()
#        plt.show()
