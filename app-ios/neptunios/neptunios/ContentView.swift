import SwiftUI
import MapKit

struct ContentView: View {
    @StateObject private var viewModel = MapViewModel()
    
    var body: some View {
        ZStack {
            // Карта на повний екран
            MapView(tracks: viewModel.tracks)
                .ignoresSafeArea(.all)
            
            VStack(spacing: 0) {
                // ВЕРХНІЙ ЗАГОЛОВОК (як в Android)
                HStack {
                    Text("NEPTUN")
                        .font(.system(size: 24, weight: .bold))
                        .foregroundColor(.white)
                    
                    Spacer()
                    
                    // Лічильник маркерів (синій бейдж)
                    if !viewModel.tracks.isEmpty {
                        Text("\(viewModel.tracks.count)")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(.white)
                            .frame(minWidth: 28, minHeight: 24)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(
                                Capsule()
                                    .fill(Color(red: 0x3B/255.0, green: 0x82/255.0, blue: 0xF6/255.0))
                            )
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(
                    Color(red: 0x0F/255.0, green: 0x17/255.0, blue: 0x2A/255.0)
                        .opacity(0.95)
                )
                
                Spacer()
                
                // НИЖНЯ ПАНЕЛЬ (як в Android)
                VStack(spacing: 16) {
                    // Кількість загроз
                    HStack {
                        Text("📍 Загроз на карті:")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundColor(.white)
                        
                        Spacer()
                        
                        Text("\(viewModel.tracks.count)")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundColor(Color(red: 0x3B/255.0, green: 0x82/255.0, blue: 0xF6/255.0))
                    }
                    
                    // Кнопка оновлення (ВЕЛИКА СИНЯ як в Android)
                    Button(action: {
                        viewModel.loadEvents()
                    }) {
                        HStack(spacing: 12) {
                            Image(systemName: "arrow.clockwise")
                                .font(.system(size: 18, weight: .semibold))
                            Text("Оновити дані")
                                .font(.system(size: 16, weight: .semibold))
                        }
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(Color(red: 0x3B/255.0, green: 0x82/255.0, blue: 0xF6/255.0))
                        )
                    }
                    .disabled(viewModel.isLoading)
                    .opacity(viewModel.isLoading ? 0.6 : 1.0)
                    
                    // Індикатор завантаження
                    if viewModel.isLoading {
                        HStack(spacing: 8) {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                .scaleEffect(0.8)
                            Text("Завантаження...")
                                .font(.system(size: 14))
                                .foregroundColor(.white.opacity(0.8))
                        }
                        .padding(.vertical, 4)
                    }
                    
                    // Помилка (якщо є)
                    if let error = viewModel.errorMessage {
                        Text(error)
                            .font(.system(size: 12))
                            .foregroundColor(Color(red: 0xEF/255.0, green: 0x44/255.0, blue: 0x44/255.0))
                            .padding(10)
                            .frame(maxWidth: .infinity)
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(Color.black.opacity(0.6))
                            )
                    }
                    
                    // Індикатор авто-оновлення (як в Android)
                    if viewModel.isAutoRefreshEnabled {
                        HStack(spacing: 6) {
                            Image(systemName: "arrow.clockwise.circle.fill")
                                .font(.system(size: 12))
                            Text("Авто-оновлення: 60 сек")
                                .font(.system(size: 12))
                        }
                        .foregroundColor(.white.opacity(0.6))
                        .padding(.top, 4)
                    }
                }
                .padding(16)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(Color(red: 0x0F/255.0, green: 0x17/255.0, blue: 0x2A/255.0).opacity(0.95))
                )
                .padding(.horizontal, 16)
                .padding(.bottom, 16)
            }
        }
        .onAppear {
            viewModel.loadEvents()
        }
    }
}

#Preview {
    ContentView()
}
