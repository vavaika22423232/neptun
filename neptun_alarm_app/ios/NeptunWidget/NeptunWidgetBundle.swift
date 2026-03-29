import ActivityKit
import WidgetKit
import SwiftUI

@main
struct NeptunWidgetBundle: WidgetBundle {
    var body: some Widget {
        NeptunWidget()
        if #available(iOS 16.2, *) {
            NeptunLiveActivity()
        }
    }
}
