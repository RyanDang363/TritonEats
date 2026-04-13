import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import * as Location from "expo-location";
import MapView, { Marker, Region } from "react-native-maps";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useAuth } from "@/context/AuthContext";
import { getRecommendations } from "@/lib/api";
import Colors from "@/constants/Colors";

const UCSD_CENTER: Region = {
  latitude: 32.8801,
  longitude: -117.234,
  latitudeDelta: 0.018,
  longitudeDelta: 0.018,
};

const DINING_HALLS = [
  { name: "64 Degrees", latitude: 32.8747361891314, longitude: -117.24203767174787 },
  { name: "Bistro", latitude: 32.887956067919724, longitude: -117.24206241257659 },
  { name: "Canyon Vista", latitude: 32.88403633357428, longitude: -117.23325809538268 },
  { name: "Club Med", latitude: 32.87536044758696, longitude: -117.23494381718517 },
  { name: "Foodworx", latitude: 32.878896028759875, longitude: -117.2304497515708 },
  { name: "Oceanview", latitude: 32.883301890248696, longitude: -117.24265415125186 },
  { name: "Sixth College", latitude: 32.87991281921435, longitude: -117.24157902483346 },
  { name: "Ventanas", latitude: 32.88607466442636, longitude: -117.24257422659045 },
];

type LocationMode = "gps" | "pin";

export default function HomeScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const mapRef = useRef<MapView>(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<LocationMode>("gps");
  const [pinCoord, setPinCoord] = useState<{ latitude: number; longitude: number } | null>(null);
  const [userLocation, setUserLocation] = useState<{ latitude: number; longitude: number } | null>(null);

  useEffect(() => {
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === "granted") {
        const loc = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        setUserLocation({ latitude: loc.coords.latitude, longitude: loc.coords.longitude });
      }
    })();
  }, []);

  const handleMapPress = (e: any) => {
    if (mode !== "pin") return;
    setPinCoord(e.nativeEvent.coordinate);
  };

  const handleFindFood = async () => {
    if (!user) return;
    setLoading(true);

    try {
      let lat: number;
      let lng: number;

      if (mode === "pin") {
        if (!pinCoord) {
          Alert.alert("No pin set", "Tap the map to drop a pin first.");
          setLoading(false);
          return;
        }
        lat = pinCoord.latitude;
        lng = pinCoord.longitude;
      } else {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== "granted") {
          Alert.alert(
            "Location needed",
            "We need your location to find the closest dining options. Please enable location in Settings."
          );
          setLoading(false);
          return;
        }
        const loc = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        lat = loc.coords.latitude;
        lng = loc.coords.longitude;
      }

      const recs = await getRecommendations(user.id, lat, lng);

      router.push({
        pathname: "/recommend",
        params: {
          data: JSON.stringify(recs),
          userLat: String(lat),
          userLng: String(lng),
        },
      });
    } catch (e: any) {
      Alert.alert("Error", e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.heroCard}>
        <Image source={require("../../assets/images/logo.png")} style={styles.logo} />
        <Text style={styles.greeting}>What's good, Triton?</Text>
        <Text style={styles.tagline}>Find your next meal on campus</Text>
      </View>

      <View style={styles.mapContainer}>
        <MapView
          ref={mapRef}
          style={styles.map}
          initialRegion={UCSD_CENTER}
          showsUserLocation={mode === "gps"}
          showsMyLocationButton={false}
          onPress={handleMapPress}
        >
          {DINING_HALLS.map((hall) => (
            <Marker
              key={hall.name}
              coordinate={{ latitude: hall.latitude, longitude: hall.longitude }}
              title={hall.name}
              pinColor={Colors.gold}
            />
          ))}

          {mode === "pin" && pinCoord && (
            <Marker
              coordinate={pinCoord}
              title="Your pin"
              pinColor={Colors.navy}
            />
          )}
        </MapView>

        <View style={styles.toggleContainer}>
          <View style={styles.toggle}>
            <Pressable
              style={[styles.toggleOption, mode === "gps" && styles.toggleActive]}
              onPress={() => setMode("gps")}
            >
              <FontAwesome
                name="crosshairs"
                size={14}
                color={mode === "gps" ? "#FFFFFF" : Colors.light.textSecondary}
              />
              <Text style={[styles.toggleText, mode === "gps" && styles.toggleTextActive]}>
                My Location
              </Text>
            </Pressable>
            <Pressable
              style={[styles.toggleOption, mode === "pin" && styles.toggleActive]}
              onPress={() => setMode("pin")}
            >
              <FontAwesome
                name="map-pin"
                size={14}
                color={mode === "pin" ? "#FFFFFF" : Colors.light.textSecondary}
              />
              <Text style={[styles.toggleText, mode === "pin" && styles.toggleTextActive]}>
                Drop Pin
              </Text>
            </Pressable>
          </View>
        </View>

        {mode === "pin" && !pinCoord && (
          <View style={styles.hintContainer}>
            <Text style={styles.hintText}>Tap the map to drop a pin</Text>
          </View>
        )}
      </View>

      <View style={styles.body}>
        <Pressable
          style={({ pressed }) => [
            styles.findButton,
            loading && styles.findButtonDisabled,
            pressed && !loading && { transform: [{ scale: 0.97 }] },
          ]}
          onPress={handleFindFood}
          disabled={loading}
        >
          {loading ? (
            <View style={styles.loadingRow}>
              <ActivityIndicator color="#FFFFFF" size="small" />
              <Text style={styles.findButtonText}>Finding your picks...</Text>
            </View>
          ) : (
            <View style={styles.buttonInner}>
              <FontAwesome
                name={mode === "pin" ? "map-pin" : "location-arrow"}
                size={20}
                color="#FFFFFF"
              />
              <Text style={styles.findButtonText}>
                {mode === "pin" ? "Find Food From Pin" : "Find Food Near Me"}
              </Text>
            </View>
          )}
        </Pressable>

      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.light.background,
  },
  heroCard: {
    backgroundColor: Colors.navy,
    marginHorizontal: 16,
    marginTop: 12,
    borderRadius: 20,
    paddingTop: 0,
    paddingBottom: 16,
    paddingHorizontal: 24,
    alignItems: "center",
  },
  logo: {
    width: 100,
    height: 100,
    resizeMode: "contain",
    marginBottom: -16,
  },
  greeting: {
    fontSize: 20,
    fontWeight: "800",
    color: "#FFFFFF",
    marginBottom: 4,
  },
  tagline: {
    fontSize: 13,
    color: "rgba(255,255,255,0.55)",
    textAlign: "center",
  },
  mapContainer: {
    marginHorizontal: 16,
    marginTop: 12,
    borderRadius: 20,
    overflow: "hidden",
    height: 340,
    shadowColor: Colors.light.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 6,
  },
  map: {
    width: "100%",
    height: "100%",
  },
  toggleContainer: {
    position: "absolute",
    top: 12,
    left: 0,
    right: 0,
    alignItems: "center",
  },
  toggle: {
    flexDirection: "row",
    backgroundColor: "rgba(255,255,255,0.95)",
    borderRadius: 20,
    padding: 3,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 4,
  },
  toggleOption: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 17,
  },
  toggleActive: {
    backgroundColor: Colors.navy,
  },
  toggleText: {
    fontSize: 13,
    fontWeight: "600",
    color: Colors.light.textSecondary,
  },
  toggleTextActive: {
    color: "#FFFFFF",
  },
  hintContainer: {
    position: "absolute",
    bottom: 12,
    left: 0,
    right: 0,
    alignItems: "center",
  },
  hintText: {
    backgroundColor: "rgba(24,43,73,0.85)",
    color: "#FFFFFF",
    fontSize: 13,
    fontWeight: "600",
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    overflow: "hidden",
  },
  body: {
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  findButton: {
    backgroundColor: Colors.gold,
    borderRadius: 16,
    paddingVertical: 18,
    paddingHorizontal: 24,
    alignItems: "center",
    shadowColor: Colors.gold,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 6,
  },
  findButtonDisabled: { opacity: 0.7 },
  buttonInner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  findButtonText: {
    fontSize: 17,
    fontWeight: "700",
    color: "#FFFFFF",
  },
  loadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
});
