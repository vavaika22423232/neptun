import Foundation
import Combine

// MapViewModel - точно як в Android MapViewModel
@MainActor
class MapViewModel: ObservableObject {
    @Published var tracks: [AlarmTrack] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var isAutoRefreshEnabled = true
    
    private var refreshTimer: Timer?
    
    init() {
        Task {
            await loadEvents()
        }
        startAutoRefresh()
    }
    
    func loadEvents() async {
        isLoading = true
        errorMessage = nil
        
        do {
            let response = try await NetworkService.shared.fetchAlarmData()
            self.tracks = response.tracks ?? []
            self.isLoading = false
            print("📍 MapViewModel: Loaded \(self.tracks.count) threat markers")
        } catch {
            self.errorMessage = "Помилка завантаження: \(error.localizedDescription)"
            self.isLoading = false
            print("❌ MapViewModel Error: \(error)")
        }
    }
    
    private func startAutoRefresh() {
        // Auto-refresh every 60 seconds (як в Android)
        refreshTimer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            Task { @MainActor in
                await self?.loadEvents()
            }
        }
    }
    
    deinit {
        refreshTimer?.invalidate()
    }
}
