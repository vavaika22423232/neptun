//
//  neptuniosApp.swift
//  neptunios
//
//  Created by Владимир Малик on 13.11.2025.
//

import SwiftUI

@main
struct neptuniosApp: App {
    
    init() {
        // Налаштування мережі
        configureNetworking()
    }
    
    var body: some Scene {
        WindowGroup {
            MainNavigationView()
        }
    }
    
    private func configureNetworking() {
        // Дозволяємо HTTP запити (якщо потрібно)
        // В Info.plist додано NSAppTransportSecurity
    }
}
