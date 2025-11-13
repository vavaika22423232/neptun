import SwiftUI
import MapKit

// ContentView - точно як Android MapScreen
struct ContentView: View {
    @StateObject private var viewModel = MapViewModel()
    
    var body: some View {
        ZStack {
            // Map з маркерами (як в Android)
            MapView(tracks: viewModel.tracks)
                .ignoresSafeArea()
            
            // Header (як в Android)
            VStack {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("NEPTUN")
                            .font(.system(size: 24, weight: .bold))
                            .foregroundColor(Color(hex: "3B82F6"))
                        
                        HStack(spacing: 8) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundColor(Color(hex: "3B82F6"))
                                .font(.system(size: 14))
                            
                            Text("\(viewModel.tracks.count)")
                                .font(.system(size: 16, weight: .medium))
                                .foregroundColor(.white)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(Color(hex: "3B82F6").opacity(0.2))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 12)
                                        .stroke(Color(hex: "3B82F6"), lineWidth: 1)
                                )
                        )
                    }
                    
                    Spacer()
                    
                    // Refresh button (як в Android)
                    Button(action: {
                        Task {
                            await viewModel.loadEvents()
                        }
                    }) {
                        Image(systemName: "arrow.clockwise")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundColor(Color(hex: "3B82F6"))
                            .frame(width: 40, height: 40)
                            .background(
                                Circle()
                                    .fill(Color(hex: "3B82F6").opacity(0.2))
                            )
                    }
                }
                .padding()
                .background(
                    Color(hex: "0F172A")
                        .opacity(0.9)
                        .shadow(color: .black.opacity(0.3), radius: 8)
                )
                
                if !viewModel.tracks.isEmpty {
                    Text("📍 Загроз на карті: \(viewModel.tracks.count)")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(Color(hex: "EF4444"))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(
                            Color(hex: "0F172A")
                                .opacity(0.9)
                        )
                }
                
                Spacer()
            }
            
            // Loading indicator (як в Android)
            if viewModel.isLoading {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: Color(hex: "3B82F6")))
                    .scaleEffect(1.5)
            }
            
            // Error message (як в Android)
            if let error = viewModel.errorMessage {
                VStack {
                    Spacer()
                    Text(error)
                        .font(.system(size: 14))
                        .foregroundColor(.white)
                        .padding()
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(Color(hex: "EF4444").opacity(0.9))
                        )
                        .padding()
                }
            }
            
            // Auto-refresh indicator (як в Android)
            if viewModel.isAutoRefreshEnabled {
                VStack {
                    Spacer()
                    HStack {
                        Spacer()
                        Text("🔄 Auto")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(.white)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(
                                RoundedRectangle(cornerRadius: 20)
                                    .fill(Color(hex: "3B82F6").opacity(0.8))
                            )
                            .padding()
                    }
                }
            }
        }
    }
}

// MARK: - Extensions

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
