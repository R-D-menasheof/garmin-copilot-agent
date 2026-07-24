# Keep rules for auth plugins that use reflection / dynamic class loading.
# Needed if R8/minification (minifyEnabled) is ever turned back on for release.
# flutter_appauth ships no consumer rules, so R8 would otherwise strip these.

-keep class net.openid.appauth.** { *; }
-keep class io.crossingthestreams.flutterappauth.** { *; }
-dontwarn net.openid.appauth.**

# flutter_secure_storage
-keep class com.it_nomads.fluttersecurestorage.** { *; }
