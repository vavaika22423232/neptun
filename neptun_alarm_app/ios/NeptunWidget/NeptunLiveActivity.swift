import ActivityKit
import WidgetKit
import SwiftUI

// MARK: - Activity Attributes

struct NeptunAlarmAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        var threatType: String
        var threatCount: Int
        var startTime: Date
        var isAlarm: Bool
    }

    var region: String
}

// MARK: - Live Activity Widget

struct NeptunLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: NeptunAlarmAttributes.self) { context in
            // Lock Screen presentation
            LockScreenView(
                region: context.attributes.region,
                threatType: context.state.threatType,
                threatCount: context.state.threatCount,
                startTime: context.state.startTime,
                isAlarm: context.state.isAlarm
            )
            .activityBackgroundTint(Color(red: 0.08, green: 0.10, blue: 0.14))
        } dynamicIsland: { context in
            DynamicIsland {
                // Expanded view (long-press)
                DynamicIslandExpandedRegion(.leading) {
                    HStack(spacing: 8) {
                        Image(systemName: "shield.fill")
                            .foregroundColor(context.state.isAlarm ? Color(red: 1.0, green: 0.32, blue: 0.32) : Color(red: 0.4, green: 0.73, blue: 0.42))
                        Text(context.state.threatType)
                            .font(.caption.bold())
                            .foregroundColor(.white)
                    }
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text("\(context.state.threatCount)")
                        .font(.title2.bold())
                        .foregroundColor(.white)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(context.attributes.region)
                            .font(.subheadline)
                            .foregroundColor(.white.opacity(0.8))
                        Text(context.state.isAlarm ? "ТРИВОГА" : "Все спокійно")
                            .font(.caption.bold())
                            .foregroundColor(context.state.isAlarm ? Color(red: 1.0, green: 0.32, blue: 0.32) : Color(red: 0.4, green: 0.73, blue: 0.42))
                        Text(timerInterval: context.state.startTime...Date().addingTimeInterval(3600), countsDown: false)
                            .font(.caption2.monospacedDigit())
                            .foregroundColor(.white.opacity(0.6))
                    }
                }
            } compactLeading: {
                Image(systemName: "shield.fill")
                    .foregroundColor(context.state.isAlarm ? Color(red: 1.0, green: 0.32, blue: 0.32) : Color(red: 0.4, green: 0.73, blue: 0.42))
            } compactTrailing: {
                Text(context.attributes.region)
                    .font(.caption2)
                    .foregroundColor(.white)
                    .lineLimit(1)
            } minimal: {
                Image(systemName: "shield.fill")
                    .foregroundColor(context.state.isAlarm ? Color(red: 1.0, green: 0.32, blue: 0.32) : Color(red: 0.4, green: 0.73, blue: 0.42))
            }
        }
    }
}

// MARK: - Lock Screen View

struct LockScreenView: View {
    let region: String
    let threatType: String
    let threatCount: Int
    let startTime: Date
    let isAlarm: Bool

    private static let timeFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "HH:mm"
        return f
    }()

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("NEPTUN")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.white)
                Spacer()
                Text(Self.timeFormatter.string(from: startTime))
                    .font(.system(size: 10))
                    .foregroundColor(.white.opacity(0.6))
            }

            Text(isAlarm ? "ТРИВОГА" : "Все спокійно")
                .font(.system(size: 20, weight: .semibold))
                .foregroundColor(isAlarm ? Color(red: 1.0, green: 0.32, blue: 0.32) : Color(red: 0.4, green: 0.73, blue: 0.42))

            Text(region)
                .font(.system(size: 12))
                .foregroundColor(.white.opacity(0.6))
                .lineLimit(1)

            if threatCount > 0 {
                Text("\(threatType): \(threatCount)")
                    .font(.system(size: 11))
                    .foregroundColor(Color(red: 1.0, green: 0.67, blue: 0.57))
            }

            Text(timerInterval: startTime...Date().addingTimeInterval(3600), countsDown: false)
                .font(.caption2.monospacedDigit())
                .foregroundColor(.white.opacity(0.45))
        }
        .padding(16)
    }
}
