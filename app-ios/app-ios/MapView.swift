import SwiftUI
import MapKit

// MapView - точно як Android MapScreen з OSMDroid
struct MapView: UIViewRepresentable {
    let tracks: [AlarmTrack]
    
    func makeUIView(context: Context) -> MKMapView {
        let mapView = MKMapView()
        mapView.delegate = context.coordinator
        
        // Ukraine center (як в Android)
        let ukraineCenter = CLLocationCoordinate2D(latitude: 48.3794, longitude: 31.1656)
        let region = MKCoordinateRegion(
            center: ukraineCenter,
            span: MKCoordinateSpan(latitudeDelta: 8.0, longitudeDelta: 8.0)
        )
        mapView.setRegion(region, animated: false)
        
        // Load Ukraine border (як в Android UkraineBorderLoader)
        Task {
            await context.coordinator.loadUkraineBorder(mapView: mapView)
        }
        
        return mapView
    }
    
    func updateUIView(_ mapView: MKMapView, context: Context) {
        // Remove old annotations (крім кордону)
        let existingAnnotations = mapView.annotations.filter { !($0 is MKPolygon) }
        mapView.removeAnnotations(existingAnnotations)
        
        print("MapView: Adding \(tracks.count) markers")
        
        // Add new markers (як в Android)
        for track in tracks {
            let annotation = ThreatAnnotation(track: track)
            mapView.addAnnotation(annotation)
        }
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }
    
    // MARK: - Coordinator
    class Coordinator: NSObject, MKMapViewDelegate {
        private var iconCache: [String: UIImage] = [:]
        
        // Load Ukraine border (як в Android UkraineBorderLoader)
        func loadUkraineBorder(mapView: MKMapView) async {
            do {
                let url = URL(string: "https://neptun.in.ua/static/geoBoundaries-UKR-ADM0_simplified.geojson")!
                let (data, _) = try await URLSession.shared.data(from: url)
                let geoJSON = try JSONDecoder().decode(GeoJSONFeatureCollection.self, from: data)
                
                if let feature = geoJSON.features.first,
                   let coordinates = feature.geometry.coordinates.first {
                    
                    var points: [CLLocationCoordinate2D] = []
                    for coord in coordinates {
                        if coord.count >= 2 {
                            let lng = coord[0]
                            let lat = coord[1]
                            points.append(CLLocationCoordinate2D(latitude: lat, longitude: lng))
                        }
                    }
                    
                    await MainActor.run {
                        // Add border polygon
                        let polygon = MKPolygon(coordinates: points, count: points.count)
                        mapView.addOverlay(polygon, level: .aboveLabels)
                        
                        print("✅ Ukraine border loaded: \(points.count) points")
                    }
                }
            } catch {
                print("❌ Failed to load Ukraine border: \(error)")
            }
        }
        
        // Custom annotation view з іконками (як в Android ThreatIconLoader)
        func mapView(_ mapView: MKMapView, viewFor annotation: MKAnnotation) -> MKAnnotationView? {
            guard let threatAnnotation = annotation as? ThreatAnnotation else {
                return nil
            }
            
            let identifier = "ThreatMarker"
            var annotationView = mapView.dequeueReusableAnnotationView(withIdentifier: identifier)
            
            if annotationView == nil {
                annotationView = MKAnnotationView(annotation: annotation, reuseIdentifier: identifier)
                annotationView?.canShowCallout = true
            } else {
                annotationView?.annotation = annotation
            }
            
            // Load custom icon (як в Android ThreatIconLoader)
            let iconURL = ThreatIconLoader.getIconURL(
                markerIcon: threatAnnotation.track.markerIcon,
                threatType: threatAnnotation.track.threatType
            )
            
            // Check cache
            if let cachedImage = iconCache[iconURL] {
                annotationView?.image = cachedImage
            } else {
                // Load icon asynchronously
                Task {
                    if let url = URL(string: iconURL),
                       let data = try? Data(contentsOf: url),
                       let image = UIImage(data: data) {
                        
                        // Resize to 48x48 (як в Android - 48dp)
                        let size = CGSize(width: 48, height: 48)
                        let renderer = UIGraphicsImageRenderer(size: size)
                        let resizedImage = renderer.image { _ in
                            image.draw(in: CGRect(origin: .zero, size: size))
                        }
                        
                        await MainActor.run {
                            self.iconCache[iconURL] = resizedImage
                            annotationView?.image = resizedImage
                        }
                        
                        print("✅ Loaded icon: \(threatAnnotation.track.threatType ?? "default")")
                    }
                }
                
                // Default icon while loading
                annotationView?.image = UIImage(systemName: "exclamationmark.triangle.fill")?
                    .withTintColor(.systemRed, renderingMode: .alwaysOriginal)
            }
            
            return annotationView
        }
        
        // Border rendering (як в Android з #475569 кольором)
        func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {
            if let polygon = overlay as? MKPolygon {
                let renderer = MKPolygonRenderer(polygon: polygon)
                renderer.strokeColor = UIColor(red: 0x47/255, green: 0x55/255, blue: 0x69/255, alpha: 0.86)
                renderer.lineWidth = 4
                renderer.fillColor = .clear
                return renderer
            }
            return MKOverlayRenderer(overlay: overlay)
        }
    }
}

// MARK: - Custom Annotation

class ThreatAnnotation: NSObject, MKAnnotation {
    let track: AlarmTrack
    var coordinate: CLLocationCoordinate2D
    var title: String?
    var subtitle: String?
    
    init(track: AlarmTrack) {
        self.track = track
        self.coordinate = CLLocationCoordinate2D(
            latitude: track.latitude,
            longitude: track.longitude
        )
        self.title = track.place ?? track.threatType ?? "Загроза"
        self.subtitle = track.text
        super.init()
    }
}

// MARK: - Icon Loader (як в Android ThreatIconLoader)

class ThreatIconLoader {
    private static let baseURL = "https://neptun.in.ua/static"
    
    static func getIconURL(markerIcon: String?, threatType: String?) -> String {
        // Priority: marker_icon > threat_type (як в Android)
        if let markerIcon = markerIcon {
            if markerIcon.starts(with: "http") {
                return markerIcon
            } else if markerIcon.starts(with: "/") {
                return "https://neptun.in.ua\(markerIcon)"
            } else {
                return "\(baseURL)/\(markerIcon)"
            }
        }
        
        // Fallback to threat type (як в Android)
        let iconName = getIconName(for: threatType?.lowercased() ?? "default")
        return "\(baseURL)/\(iconName)"
    }
    
    private static func getIconName(for threatType: String) -> String {
        // Mapping з Android ThreatIconLoader
        switch threatType {
        case "shahed": return "shahed.png"
        case "raketa": return "raketa.png"
        case "kab": return "rszv.png"
        case "avia": return "avia.png"
        case "pvo", "rozved": return "rozved.png"
        case "rszv", "mlrs": return "rszv.png"
        case "vibuh": return "vibuh.png"
        case "alarm": return "trivoga.png"
        case "alarm_cancel": return "vidboi.png"
        case "artillery", "obstril": return "obstril.png"
        case "fpv": return "fpv.png"
        case "pusk": return "pusk.png"
        default: return "default.png"
        }
    }
}

// MARK: - GeoJSON Models (для кордонів України)

struct GeoJSONFeatureCollection: Codable {
    let features: [GeoJSONFeature]
}

struct GeoJSONFeature: Codable {
    let geometry: GeoJSONGeometry
}

struct GeoJSONGeometry: Codable {
    let type: String
    let coordinates: [[[Double]]]
}
