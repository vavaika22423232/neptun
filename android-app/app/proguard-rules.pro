# Add project specific ProGuard rules here.
-keep class com.neptun.alarmmap.data.model.** { *; }
-keepattributes Signature
-keepattributes *Annotation*
-dontwarn okhttp3.**
-dontwarn retrofit2.**
