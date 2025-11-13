import Foundation

// NetworkService - точно як в Android NeptunApiService
class NetworkService {
    static let shared = NetworkService()
    private let baseURL = "https://neptun.in.ua"
    
    private init() {}
    
    func fetchAlarmData() async throws -> ApiResponse {
        guard let url = URL(string: "\(baseURL)/data") else {
            throw NetworkError.invalidURL
        }
        
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw NetworkError.invalidResponse
        }
        
        let decoder = JSONDecoder()
        let apiResponse = try decoder.decode(ApiResponse.self, from: data)
        
        print("✅ NetworkService: Loaded \(apiResponse.tracks?.count ?? 0) tracks")
        return apiResponse
    }
}

enum NetworkError: Error {
    case invalidURL
    case invalidResponse
    case decodingError
}
