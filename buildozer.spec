[app]
# (str) Title of your application
title = Snaglist Pro

# (str) Package name
package.name = snaglistpro

# (str) Package domain
package.domain = com.example

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas,txt

# (list) List of inclusions using pattern matching
source.include_patterns = android_app/**, snaglist_pro/**, desktop_app.py

# (str) Application versioning (method 1)
version = 0.1.0

# (list) Application requirements
requirements = python3,kivy,openpyxl,Pillow,rapidfuzz,pyyaml

# (str) Custom source folders for requirements
# requirements.source = /path/to/dir

# (str) Presplash of the application
# presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
# icon.filename = %(source.dir)s/data/icon.png

# (list) Supported orientations
orientation = portrait

# (bool) Indicate if the app should be fullscreen or not
fullscreen = 0

# (list) Android permissions
android.permissions = INTERNET

# (int) Target Android API, should be as high as possible
android.api = 31

# (int) Minimum API your APK will support
android.minapi = 23

# (str) Android NDK directory (if empty, it will use a downloaded one)
# android.ndk_path =

# (str) Android SDK directory (if empty, it will use a downloaded one)
# android.sdk_path =

# (bool) Use --private data directory instead of --dir
android.private_storage = 1

# (str) Android entry point, default is main.py:main
# android.entrypoint = org.renpy.android.PythonActivity

# (bool) Use --orientation orientation
# android.use_androidx = True

# (str) The Android arch to build for
# android.archs = arm64-v8a, armeabi-v7a

# (str) Command line to run
# command =

# (list) list of Python files that should be compiled
# p4a.source_dir =

# (str) python-for-android branch to use, stable is HEAD
# p4a.branch = master

# (str) extra source code to include in the package
# extras.source_dirs =

# (str) Additional source fields
# extras =

# (list) Application and library modules to install
#android.add_jars =
#android.add_assets =
#android.add_libs =
#android.add_src =

# (bool) If True, then convert the app to an APK file
# p4a.format = apk

# (str) Python version to use
# p4a.python_version = 3.11

# (bool) If True, use QString and Kotlin instead of SDL2
# p4a.use_kotlin = True

# (list) Extra modules that will be imported by Python
# android.extra =

# (list) Extra commands to run
# android.extra_commands =

# (list) Extra Python packages to be installed
# android.extra_packages =

# (list) Extra Java jars to be added
# android.add_jars =

# (list) Extra Java source folders
# android.add_src =

# (str) The name of the main class
# android.main_class =

# (str) The activity name
# android.activity_class_name = MainActivity

# (str) The app will be built for Android 10+
# android.sdk_version = 31

# (bool) Indicate if the Android app should be launched on startup
# android.launcher = true

# (str) The folder where the APK will be saved after build
# bin_dir = ./bin

# (bool) Set to True if you want to build a release APK
# release = 1

# (list) Application test packages
# tests =
