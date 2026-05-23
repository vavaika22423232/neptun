import WidgetKit
import SwiftUI

private let appGroupId = "group.com.neptunalarm.neptunAlarmApp"
private let widgetKind = "NeptunWidget"

struct NeptunEntry: TimelineEntry {
    let date: Date
    let data: WidgetData
}

struct WidgetData {
    let region: String
    let isAlarm: Bool
    let totalAlarms: Int
    let statusText: String?
    let threatsDetail: String?
    let lastUpdate: Date

    static func load() -> WidgetData {
        let defaults = UserDefaults(suiteName: appGroupId)

        let region = defaults?.string(forKey: "widget_region") ?? "Україна"
        let isAlarm = defaults?.bool(forKey: "widget_is_alarm") ?? false
        let totalAlarms = defaults?.integer(forKey: "widget_total_alarms") ?? 0
        let statusText = defaults?.string(forKey: "widget_status_text")

        let dronesCount = defaults?.integer(forKey: "widget_drones_count") ?? 0
        let missilesCount = defaults?.integer(forKey: "widget_missiles_count") ?? 0
        let kabCount = defaults?.integer(forKey: "widget_kab_count") ?? 0
        let ballisticCount = defaults?.integer(forKey: "widget_ballistic_count") ?? 0
        let totalThreats = defaults?.integer(forKey: "widget_total_threats") ?? 0

        var threatsDetail: String? = nil
        if statusText == nil && totalThreats > 0 {
            var parts: [String] = []
            if dronesCount > 0 { parts.append("Шахеди: \(dronesCount)") }
            if missilesCount > 0 { parts.append("Ракети: \(missilesCount)") }
            if kabCount > 0 { parts.append("КАБ: \(kabCount)") }
            if ballisticCount > 0 { parts.append("Балістика: \(ballisticCount)") }
            if !parts.isEmpty {
                threatsDetail = parts.joined(separator: "  •  ")
            }
        }

        let lastUpdateMs = defaults?.double(forKey: "widget_last_update") ?? 0
        let lastUpdate: Date
        if lastUpdateMs > 0 {
            lastUpdate = Date(timeIntervalSince1970: lastUpdateMs / 1000)
        } else {
            lastUpdate = Date()
        }

        return WidgetData(
            region: region,
            isAlarm: isAlarm,
            totalAlarms: totalAlarms,
            statusText: statusText,
            threatsDetail: threatsDetail,
            lastUpdate: lastUpdate
        )
    }
}

struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> NeptunEntry {
        NeptunEntry(date: Date(), data: WidgetData.load())
    }

    func getSnapshot(in context: Context, completion: @escaping (NeptunEntry) -> Void) {
        completion(NeptunEntry(date: Date(), data: WidgetData.load()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<NeptunEntry>) -> Void) {
        let entry = NeptunEntry(date: Date(), data: WidgetData.load())
        let nextUpdate = Calendar.current.date(byAdding: .minute, value: 5, to: Date()) ?? Date().addingTimeInterval(300)
        completion(Timeline(entries: [entry], policy: .after(nextUpdate)))
    }
}

struct NeptunWidgetView: View {
    let entry: NeptunEntry

    private static let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        return formatter
    }()

    private func alarmsText(_ total: Int) -> String {
        if total == 0 { return "Немає тривог" }
        if total == 1 { return "1 область з тривогою" }
        if (2...4).contains(total) { return "\(total) області з тривогою" }
        return "\(total) областей з тривогою"
    }

    private var statusDisplayText: String {
        if let statusText = entry.data.statusText, !statusText.isEmpty {
            return statusText
        }
        return entry.data.isAlarm ? "ТРИВОГА" : "Все спокійно"
    }

    private var statusColor: Color {
        if let statusText = entry.data.statusText, !statusText.isEmpty {
            return Color(red: 1.0, green: 0.84, blue: 0.0)
        }
        return entry.data.isAlarm ? Color(red: 1.0, green: 0.32, blue: 0.32) : Color(red: 0.4, green: 0.73, blue: 0.42)
    }

    private var totalAlarmsText: String {
        if let statusText = entry.data.statusText, !statusText.isEmpty {
            return "Відкрийте додаток"
        }
        return alarmsText(entry.data.totalAlarms)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text("NEPTUN")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.white)
                Spacer()
                Text(Self.timeFormatter.string(from: entry.data.lastUpdate))
                    .font(.system(size: 10))
                    .foregroundColor(Color.white.opacity(0.6))
            }

            Text(statusDisplayText)
                .font(.system(size: 20, weight: .semibold))
                .foregroundColor(statusColor)

            Text(entry.data.region)
                .font(.system(size: 12))
                .foregroundColor(Color.white.opacity(0.6))
                .lineLimit(1)

            if let threatsDetail = entry.data.threatsDetail {
                Text(threatsDetail)
                    .font(.system(size: 11))
                    .foregroundColor(Color(red: 1.0, green: 0.67, blue: 0.57))
                    .lineLimit(2)
            }

            Text(totalAlarmsText)
                .font(.system(size: 11))
                .foregroundColor(Color.white.opacity(0.45))

            Spacer(minLength: 0)
        }
        .padding(16)
        .widgetURL(URL(string: "neptun://alarm?open=radar"))
    }
}

struct NeptunWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: widgetKind, provider: Provider()) { entry in
            if #available(iOSApplicationExtension 17.0, *) {
                NeptunWidgetView(entry: entry)
                    .containerBackground(Color(red: 0.08, green: 0.10, blue: 0.14), for: .widget)
            } else {
                NeptunWidgetView(entry: entry)
                    .background(Color(red: 0.08, green: 0.10, blue: 0.14))
            }
        }
        .configurationDisplayName("NEPTUN")
        .description("Оновлення тривог і загроз у вибраному регіоні.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
