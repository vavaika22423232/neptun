import ExpoModulesCore
import Foundation
import WidgetKit

#if canImport(ActivityKit)
import ActivityKit
#endif

private let appGroupId = "group.com.neptunalarm.neptunAlarmApp"

#if canImport(ActivityKit)
@available(iOS 16.2, *)
struct NeptunAlarmAttributes: ActivityAttributes {
  struct ContentState: Codable, Hashable {
    var threatType: String
    var threatCount: Int
    var startTime: Date
    var isAlarm: Bool
  }

  var region: String
}
#endif

public class NeptunNativeBridgeModule: Module {
  public func definition() -> ModuleDefinition {
    Name("NeptunNativeBridge")

    Function("isAvailable") {
      true
    }

    AsyncFunction("setWidgetData") { (key: String, value: Any?) in
      guard let defaults = UserDefaults(suiteName: appGroupId) else { return }
      if value == nil || value is NSNull {
        defaults.removeObject(forKey: key)
      } else if let s = value as? String {
        defaults.set(s, forKey: key)
      } else if let b = value as? Bool {
        defaults.set(b, forKey: key)
      } else if let n = value as? Int {
        defaults.set(n, forKey: key)
      } else if let n = value as? Double {
        defaults.set(n, forKey: key)
      } else {
        defaults.set("\(value!)", forKey: key)
      }
    }

    AsyncFunction("reloadWidget") {
      if #available(iOS 14.0, *) {
        WidgetCenter.shared.reloadAllTimelines()
      }
    }

    AsyncFunction("startLiveActivity") { (options: [String: Any]) in
      #if canImport(ActivityKit)
      if #available(iOS 16.2, *) {
        let region = options["region"] as? String ?? ""
        let threatType = options["threatType"] as? String ?? "air"
        let threatCount = options["threatCount"] as? Int ?? 1
        let isAlarm = options["isAlarm"] as? Bool ?? true
        let attrs = NeptunAlarmAttributes(region: region)
        let state = NeptunAlarmAttributes.ContentState(
          threatType: threatType,
          threatCount: threatCount,
          startTime: Date(),
          isAlarm: isAlarm
        )
        let content = ActivityContent(state: state, staleDate: nil)
        _ = try? Activity<NeptunAlarmAttributes>.request(
          attributes: attrs,
          content: content,
          pushType: nil
        )
      }
      #endif
    }

    AsyncFunction("updateLiveActivity") { (options: [String: Any]) in
      #if canImport(ActivityKit)
      if #available(iOS 16.2, *) {
        guard let activity = Activity<NeptunAlarmAttributes>.activities.first else { return }
        let region = options["region"] as? String ?? activity.attributes.region
        let threatType = options["threatType"] as? String ?? "air"
        let threatCount = options["threatCount"] as? Int ?? 1
        let isAlarm = options["isAlarm"] as? Bool ?? true
        let startMs = options["startTimeMs"] as? Int
        let startTime = startMs != nil ? Date(timeIntervalSince1970: Double(startMs!) / 1000) : Date()
        let state = NeptunAlarmAttributes.ContentState(
          threatType: threatType,
          threatCount: threatCount,
          startTime: startTime,
          isAlarm: isAlarm
        )
        let content = ActivityContent(state: state, staleDate: nil)
        Task { await activity.update(content) }
      }
      #endif
    }

    AsyncFunction("endLiveActivity") {
      #if canImport(ActivityKit)
      if #available(iOS 16.2, *) {
        Task {
          for activity in Activity<NeptunAlarmAttributes>.activities {
            await activity.end(nil, dismissalPolicy: .immediate)
          }
        }
      }
      #endif
    }
  }
}
