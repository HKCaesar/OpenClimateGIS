#!/bin/bash
# install geospatial dependencies

fn_create_source_dir()
{
    if ! [ -e $SRCDIR ]; then
        mkdir $SRCDIR
    fi
}

fn_install_proj()
{
    echo "starting to install Proj..."
    PROJ_SRC=$SRCDIR/proj/$PROJ_VER
    if [ -e $PROJ_DIR ]; then
        echo "    The install directory $PROJ_DIR already exists; skipping installation..."
    else
        echo "    building in $PROJ_SRC"
        mkdir -p $PROJ_SRC
        cd $PROJ_SRC
        wget http://download.osgeo.org/proj/proj-datumgrid-1.5.zip
        wget http://download.osgeo.org/proj/proj-$PROJ_VER.tar.gz
        unzip proj-datumgrid-1.5.zip -d proj-$PROJ_VER/nad/
        tar xzf proj-$PROJ_VER.tar.gz
        cd proj-$PROJ_VER
        ./configure --prefix=$PROJ_DIR > log_proj_configure.out
        make -j 4 > log_proj_make.out
        
        echo "    installing in $PROJ_DIR"
        sudo make install > log_proj_make_install.out
        sudo sh -c "echo '$PROJ_DIR/lib' > /etc/ld.so.conf.d/proj.conf" 
        sudo ldconfig
    fi
}

fn_install_geos()
{
    echo "starting to install GEOS..."
    GEOS_SRC=$SRCDIR/geos/$GEOS_VER
    if [ -e $GEOS_DIR ]; then
        echo "    The install directory $GEOS_DIR already exists; skipping installation..."
    else
        echo "    building in $GEOS_SRC"
        mkdir -p $GEOS_SRC
        cd $GEOS_SRC
        wget http://download.osgeo.org/geos/geos-$GEOS_VER.tar.bz2
        tar xjf geos-$GEOS_VER.tar.bz2
        cd geos-$GEOS_VER
        ./configure --prefix=$GEOS_DIR > log_geos_configure.out
        make -j 4 > log_geos_make.out
        
        echo "    installing in $GEOS_DIR"
        sudo make install > log_geos_make_install.out
        sudo sh -c "echo '$GEOS_DIR/lib' > /etc/ld.so.conf.d/geos.conf" 
        sudo ldconfig
    fi
    #set the GEOS_LIBRARY_PATH variable in the Django settings file
    #GEOS_LIBRARY_PATH = '$VIRTUALENV/lib/libgeos_c.so'
}

fn_install_gdal()
{
    echo "starting to install GDAL..."
    GDAL_SRC=$SRCDIR/gdal/$GDAL_VER
    if [ -e $GDAL_DIR ]; then
        echo "The install directory $GDAL_DIR already exists; skipping installation..."
    else
        echo "    building in $GDAL_SRC"
        mkdir -p $GDAL_SRC
        cd $GDAL_SRC
        wget http://download.osgeo.org/gdal/gdal-$GDAL_VER.tar.gz
        tar xzf gdal-$GDAL_VER.tar.gz
        cd gdal-$GDAL_VER
        ./configure --prefix=$GDAL_DIR --with-geos=$GEOS_DIR/bin/geos-config > log_gdal_configure.out
        #make > log_gdal_make.out
        
        #echo "    installing in $GDAL_DIR"
        #sudo make install > log_gdal_make_install.out
        #sudo sh -c "echo '$GDAL_DIR/lib' > /etc/ld.so.conf.d/gdal.conf" 
        #sudo ldconfig
    fi
}

fn_install_netcdf4()
{
    #Install libcurl (necessary for OPeNDAP functionality)::
    sudo apt-get install libcurl3 libcurl4-openssl-dev

    echo "starting to install HDF5..."
    HDF5_SRC=$SRCDIR/hdf5/$HDF5_VER
    if [ -e $HDF5_DIR ]; then
        echo "The install directory $HDF5_DIR already exists; skipping installation..."
    else
        echo "    building in $HDF5_SRC"
        mkdir -p $HDF5_SRC
        cd $HDF5_SRC
        HDF5_TAR=hdf5-$HDF5_VER.tar.gz
        wget http://www.hdfgroup.org/ftp/HDF5/current/src/$HDF5_TAR
        tar -xzvf $HDF5_TAR
        cd hdf5-$HDF5_VER
        ./configure --prefix=$HDF5_DIR --enable-shared --enable-hl > log_hdf5_configure.log
        make -j 4 > log_hdf5_make.log
        
        echo "    installing in $HDF5_DIR"
        sudo make install > log_hdf5_make_install.log 
        sudo sh -c "echo $HDF5_DIR'/lib' > /etc/ld.so.conf.d/hdf.conf" 
        sudo ldconfig
    fi
    
    echo "starting to install netCDF4..."
    NETCDF4_SRC=$SRCDIR/hdf5/$NETCDF4_VER
    if [ -e $NETCDF4_DIR ]; then
        echo "The install directory $NETCDF4_DIR already exists; skipping installation..."
    else
        echo "    building in $NETCDF4_SRC"
        mkdir -p $NETCDF4_SRC
        cd $NETCDF4_SRC
        NETCDF4_TAR=netcdf-$NETCDF4_VER.tar.gz
        wget ftp://ftp.unidata.ucar.edu/pub/netcdf/$NETCDF4_TAR
        tar -xzvf $NETCDF4_TAR
        cd netcdf-$NETCDF4_VER
        ./configure --enable-netcdf-4 --with-hdf5=$HDF5_DIR --enable-shared --enable-dap --prefix=$NETCDF4_DIR > log_netcdf_configure.log
        make -j 4 > log_netcdf_make.log 
        
        echo "    installing in $NETCDF4_DIR"
        sudo make install > log_netcdf_make_install.log
        sudo sh -c "echo $NETCDF4_DIR'/lib' > /etc/ld.so.conf.d/netcdf.conf" 
        sudo ldconfig
    fi
}

#======================================
# main
#======================================
# upgrade system
sudo apt-get -y update
sudo apt-get -y upgrade

# install dependencies
sudo apt-get install -y wget
sudo apt-get install unzip
sudo apt-get install -y gcc
sudo apt-get install -y g++
sudo apt-get install -y swig

SRCDIR=~/src
fn_create_source_dir

PROJ_VER=4.7.0
PROJ_DIR=/usr/local/proj/$PROJ_VER
fn_install_proj

GEOS_VER=3.2.2
GEOS_DIR=/usr/local/geos/$GEOS_VER
fn_install_geos

GDAL_VER=1.8.0
GDAL_DIR=/usr/local/gdal/$GDAL_VER
fn_install_gdal

HDF5_VER=1.8.6
HDF5_DIR=/usr/local/hdf5/$HDF5_VER
export HDF5_DIR  # used by netcdf4-python
NETCDF4_VER=4.1.1
NETCDF4_DIR=/usr/local/netCDF4/$NETCDF4_VER
export NETCDF4_DIR  # used by netcdf4-python
NETCDF4_PYTHON_VER=0.9.2
NETCDF4_PYTHON_SRC=$SRCDIR/netcdf4-python/$NETCDF4_PYTHON_VER
NETCDF4_PYTHON_PATH=/usr/local/netcdf4-python/$NETCDF4_PYTHON_VER
#fn_install_netcdf4


#===============================================
# Troubleshooting
#===============================================
#-----------------------------------------------
# Troubleshooting GDAL
#-----------------------------------------------
# Testing if Django recognizes GDAL
# >>> from django.contrib.gis import gdal
# >>> gdal.HAS_GDAL
# True
#
#-----------------------------------------------
# Troubleshooting PostGIS
#-----------------------------------------------
# If successful, PostGIS installs the following files/directories:
#     /usr/share/postgresql/8.4/contrib/postgis-1.5/* 
#     /usr/lib/postgresql/8.4/lib/pgxs
#     /usr/lib/postgresql/8.4/lib/postgis-1.5.so
#     /usr/lib/postgresql/8.4/bin/pgsql2shp
#     /usr/lib/postgresql/8.4/bin/shp2pgsql
