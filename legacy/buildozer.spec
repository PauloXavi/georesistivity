[app]

# (str) Package name
package.name = mykivyapp

# (str) Package domain (needed for android/ios packaging)
package.domain = org.test

# (str) Source code where the main.py live
source.include_exts = py,png,jpg,kv,atlas
source.include_patterns = assets/*,images/*.png

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,kivymd,matplotlib

# (str) Custom source folders for requirements
# Sets custom source for any requirements with recipes
# requirements.source.kivy = ../../kivy
# requirements.source.kivymd = ../../kivymd

# (list) Garden requirements
#garden_requirements = 

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/images/mylogo.png
#presplash.animated = False

# (str) Icon of the application
#icon.filename = %(source.dir)s/images/myicon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) log_level
log_level = 2

# (bool) Enable service mode
service = NameOfYourService

# (string) Android/Java package name
package.domain = org.test

# (string) Android app theme, default one are light and dark
android.theme = light

# (list) Pattern to whitelist for the whole project
#source.whitelist = (app|screens)*

# (list) Pattern to blacklist for the whole project
#source.blacklist = README.md,tests/*

# (string) Application versioning (method 1)
# version.regex = __version__ = ['"](.*)['"]
# version.filename = %(source.dir)s/main.py

# (string) Application versioning (method 2)
version = 1.0
