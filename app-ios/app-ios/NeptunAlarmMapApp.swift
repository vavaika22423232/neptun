import SwiftUI

@main
struct NeptunAlarmMapApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

// Налаштування для мережі (HTTP)
// В Xcode додайте в Info.plist проекту:
// Key: NSAppTransportSecurity
// Type: Dictionary
//   Key: NSAllowsArbitraryLoads
//   Type: Boolean
//   Value: YES
//
// Або додайте в Build Settings > Info.plist Values:
// App Transport Security Settings > Allow Arbitrary Loads = YES
