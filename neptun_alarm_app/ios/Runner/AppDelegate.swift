import Flutter
import UIKit
import UserNotifications
import FirebaseCore
import FirebaseMessaging
import AVFoundation

@main
@objc class AppDelegate: FlutterAppDelegate {
  
  private var flutterChannel: FlutterMethodChannel?
  private var audioPlayer: AVAudioPlayer?
  
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    
    // Initialize Firebase FIRST
    FirebaseApp.configure()
    
    // Configure audio session for background playback and TTS
    configureAudioSession()
    
    // Setup Flutter Method Channel for iOS-specific features
    if let controller = window?.rootViewController as? FlutterViewController {
      flutterChannel = FlutterMethodChannel(
        name: "ua.neptun.app/ios",
        binaryMessenger: controller.binaryMessenger
      )
      
      flutterChannel?.setMethodCallHandler { [weak self] call, result in
        self?.handleMethodCall(call, result: result)
      }
    }
    
    // Set delegate for foreground notification display (banner, sound, badge)
    UNUserNotificationCenter.current().delegate = self
    
    // Permission request is handled by Flutter NotificationService.initialize()
    application.registerForRemoteNotifications()
    
    // Set Firebase Messaging delegate
    Messaging.messaging().delegate = self
    
    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
  
  // MARK: - Audio Session Configuration
  private func configureAudioSession() {
    do {
      let session = AVAudioSession.sharedInstance()
      try session.setCategory(
        .playback,
        mode: .default,
        options: [.mixWithOthers, .duckOthers, .allowBluetooth, .allowBluetoothA2DP]
      )
      try session.setActive(true)
      print("✅ Audio session configured for background playback")
    } catch {
      print("❌ Audio session configuration error: \(error)")
    }
  }
  
  // MARK: - Method Channel Handler
  private func handleMethodCall(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    switch call.method {
    case "playAlarmSound":
      playAlarmSound(result: result)
    case "stopAlarmSound":
      stopAlarmSound(result: result)
    case "setVolume":
      if let args = call.arguments as? [String: Any],
         let volume = args["volume"] as? Float {
        setVolume(volume: volume, result: result)
      } else {
        result(FlutterError(code: "INVALID_ARGS", message: "Missing volume", details: nil))
      }
    case "getPlatformVersion":
      result("iOS " + UIDevice.current.systemVersion)
    case "isLowPowerModeEnabled":
      result(ProcessInfo.processInfo.isLowPowerModeEnabled)
    case "startLiveActivity":
      if let args = call.arguments as? [String: Any],
         let region = args["region"] as? String {
        let threatType = args["threatType"] as? String ?? "air"
        let threatCount = args["threatCount"] as? Int ?? 1
        let isAlarm = args["isAlarm"] as? Bool ?? true
        if #available(iOS 16.2, *) {
          LiveActivityHelper.start(region: region, threatType: threatType, threatCount: threatCount, isAlarm: isAlarm)
        }
        result(true)
      } else {
        result(FlutterError(code: "INVALID_ARGS", message: "Missing region", details: nil))
      }
    case "updateLiveActivity":
      if let args = call.arguments as? [String: Any],
         let region = args["region"] as? String {
        let threatType = args["threatType"] as? String ?? "air"
        let threatCount = args["threatCount"] as? Int ?? 1
        let isAlarm = args["isAlarm"] as? Bool ?? true
        let startTimeMs = args["startTimeMs"] as? Int
        let startTime = startTimeMs.map { Date(timeIntervalSince1970: Double($0) / 1000) } ?? Date()
        if #available(iOS 16.2, *) {
          LiveActivityHelper.update(region: region, threatType: threatType, threatCount: threatCount, isAlarm: isAlarm, startTime: startTime)
        }
        result(true)
      } else {
        result(FlutterError(code: "INVALID_ARGS", message: "Missing region", details: nil))
      }
    case "endLiveActivity":
      if #available(iOS 16.2, *) {
        LiveActivityHelper.end()
      }
      result(true)
    default:
      result(FlutterMethodNotImplemented)
    }
  }
  
  private func playAlarmSound(result: @escaping FlutterResult) {
    do {
      // Activate audio session
      try AVAudioSession.sharedInstance().setActive(true)
      
      // Try to play a bundled alarm sound, fallback to system alert
      if let soundURL = Bundle.main.url(forResource: "alarm", withExtension: "caf") ??
                         Bundle.main.url(forResource: "alarm", withExtension: "mp3") {
        audioPlayer = try AVAudioPlayer(contentsOf: soundURL)
        audioPlayer?.numberOfLoops = -1 // Loop indefinitely
        audioPlayer?.volume = 1.0
        audioPlayer?.play()
        result(true)
      } else {
        // Fallback: use system alert sound
        AudioServicesPlayAlertSound(SystemSoundID(1005))
        result(true)
      }
    } catch {
      print("❌ Play alarm sound error: \(error)")
      result(FlutterError(code: "AUDIO_ERROR", message: error.localizedDescription, details: nil))
    }
  }
  
  private func stopAlarmSound(result: @escaping FlutterResult) {
    audioPlayer?.stop()
    audioPlayer = nil
    result(true)
  }
  
  private func setVolume(volume: Float, result: @escaping FlutterResult) {
    audioPlayer?.volume = volume
    result(true)
  }
  
  // MARK: - Remote Notifications
  override func application(_ application: UIApplication,
                          didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    // Firebase proxy handles setting Messaging.messaging().apnsToken automatically.
    // We still set it manually as a safety net.
    Messaging.messaging().apnsToken = deviceToken
    
    let tokenParts = deviceToken.map { data in String(format: "%02.2hhx", data) }
    let token = tokenParts.joined()
    NSLog("✅ APNs Device Token received: %@", token)
    
    // Report to Flutter for diagnostic visibility
    flutterChannel?.invokeMethod("onAPNSTokenReceived", arguments: token)
    
    super.application(application, didRegisterForRemoteNotificationsWithDeviceToken: deviceToken)
  }
  
  override func application(_ application: UIApplication,
                          didFailToRegisterForRemoteNotificationsWithError error: Error) {
    NSLog("❌ Failed to register for remote notifications: %@", error.localizedDescription)
    
    // Report failure to Flutter for diagnostic visibility
    flutterChannel?.invokeMethod("onAPNSError", arguments: error.localizedDescription)
  }
  
  // MARK: - Background Remote Notifications (content-available: 1)
  override func application(_ application: UIApplication,
                          didReceiveRemoteNotification userInfo: [AnyHashable: Any],
                          fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void) {
    print("📬 Received background notification: \(userInfo)")
    
    // Let Firebase handle the message
    if let messageID = userInfo["gcm.message_id"] {
      print("📬 Message ID: \(messageID)")
    }
    
    // Forward to Flutter
    flutterChannel?.invokeMethod("onBackgroundNotification", arguments: userInfo)
    
    completionHandler(.newData)
  }
}

// MARK: - UNUserNotificationCenterDelegate
extension AppDelegate {
  override func userNotificationCenter(
    _ center: UNUserNotificationCenter,
    willPresent notification: UNNotification,
    withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
  ) {
    if #available(iOS 14.0, *) {
      completionHandler([.banner, .list, .badge, .sound])
    } else {
      completionHandler([.alert, .badge, .sound])
    }
  }
  
  override func userNotificationCenter(
    _ center: UNUserNotificationCenter,
    didReceive response: UNNotificationResponse,
    withCompletionHandler completionHandler: @escaping () -> Void
  ) {
    let userInfo = response.notification.request.content.userInfo
    flutterChannel?.invokeMethod("onNotificationTapped", arguments: userInfo)
    completionHandler()
  }
}

// MARK: - MessagingDelegate
extension AppDelegate: MessagingDelegate {
  func messaging(_ messaging: Messaging, didReceiveRegistrationToken fcmToken: String?) {
    print("Firebase FCM Token: \(fcmToken ?? "nil")")
    
    // Send token to Flutter
    let dataDict: [String: String] = ["token": fcmToken ?? ""]
    NotificationCenter.default.post(
      name: Notification.Name("FCMToken"),
      object: nil,
      userInfo: dataDict
    )
  }
}
