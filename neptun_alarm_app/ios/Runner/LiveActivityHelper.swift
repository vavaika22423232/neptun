import ActivityKit
import Foundation

// Must match NeptunAlarmAttributes in NeptunWidget
struct NeptunAlarmAttributes: ActivityAttributes {
    struct ContentState: Codable, Hashable {
        var threatType: String
        var threatCount: Int
        var startTime: Date
        var isAlarm: Bool
    }

    var region: String
}

@available(iOS 16.2, *)
enum LiveActivityHelper {
    static func start(region: String, threatType: String, threatCount: Int, isAlarm: Bool) {
        let attrs = NeptunAlarmAttributes(region: region)
        let state = NeptunAlarmAttributes.ContentState(
            threatType: threatType,
            threatCount: threatCount,
            startTime: Date(),
            isAlarm: isAlarm
        )
        let content = ActivityContent(state: state, staleDate: nil)
        do {
            _ = try Activity<NeptunAlarmAttributes>.request(
                attributes: attrs,
                content: content,
                pushType: nil
            )
            print("✅ Live Activity started: \(region)")
        } catch {
            print("❌ Live Activity start error: \(error)")
        }
    }

    static func update(region: String, threatType: String, threatCount: Int, isAlarm: Bool, startTime: Date) {
        guard let activity = Activity<NeptunAlarmAttributes>.activities.first else { return }
        let state = NeptunAlarmAttributes.ContentState(
            threatType: threatType,
            threatCount: threatCount,
            startTime: startTime,
            isAlarm: isAlarm
        )
        let content = ActivityContent(state: state, staleDate: nil)
        Task {
            await activity.update(content)
        }
    }

    static func end() {
        Task {
            for activity in Activity<NeptunAlarmAttributes>.activities {
                await activity.end(nil, dismissalPolicy: .immediate)
            }
            print("✅ Live Activity ended")
        }
    }
}
