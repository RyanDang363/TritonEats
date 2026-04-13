import { Linking, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import { FoodRecommendation } from "@/lib/api";
import Colors from "@/constants/Colors";

function formatPrice(price: string | null): string | null {
  if (!price) return null;
  const cleaned = price.replace(/[^0-9.]/g, "");
  if (!cleaned) return price;
  return `$${cleaned}`;
}

export default function RecommendScreen() {
  const { data, userLat, userLng } = useLocalSearchParams<{
    data: string;
    userLat: string;
    userLng: string;
  }>();
  const router = useRouter();
  const recommendations: FoodRecommendation[] = data ? JSON.parse(data) : [];

  const handleGoNow = (destLat: number, destLng: number, hallName: string) => {
    const origin = userLat && userLng ? `${userLat},${userLng}` : "";
    const destination = `${destLat},${destLng}`;

    const url = Platform.select({
      ios: `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}&destination_place_id=&travelmode=walking`,
      default: `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}&travelmode=walking`,
    })!;

    Linking.openURL(url);
  };

  if (recommendations.length === 0) {
    return (
      <View style={styles.empty}>
        <Pressable style={styles.closeButton} onPress={() => router.back()}>
          <FontAwesome name="times" size={20} color={Colors.light.textSecondary} />
        </Pressable>
        <Text style={styles.emptyIcon}>🍽️</Text>
        <Text style={styles.emptyTitle}>No matches found</Text>
        <Text style={styles.emptySubtitle}>
          Try adjusting your dietary preferences in your profile.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.wrapper}>
      <Pressable
        style={({ pressed }) => [styles.closeButton, pressed && { opacity: 0.6 }]}
        onPress={() => router.back()}
      >
        <FontAwesome name="times" size={20} color={Colors.light.textSecondary} />
      </Pressable>

      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        <Text style={styles.header}>Your Top Picks</Text>
        <Text style={styles.subheader}>
          Based on your goals, diet & location
        </Text>

        {recommendations.map((rec, i) => {
          const price = formatPrice(rec.price);
          return (
            <View key={`${rec.name}-${i}`} style={styles.card}>
              <View style={styles.cardTop}>
                <View style={styles.rankBadge}>
                  <Text style={styles.rankText}>{i + 1}</Text>
                </View>
                <View style={styles.titleBlock}>
                  <Text style={styles.foodName} numberOfLines={2}>{rec.name}</Text>
                  <View style={styles.locationRow}>
                    <FontAwesome name="map-marker" size={12} color={Colors.light.textTertiary} />
                    <Text style={styles.location}>
                      {rec.dining_hall} · {rec.station}
                    </Text>
                  </View>
                </View>
              </View>

              <View style={styles.metaRow}>
                {rec.walking_minutes != null && (
                  <View style={styles.metaPill}>
                    <FontAwesome name="male" size={12} color={Colors.light.textSecondary} />
                    <Text style={styles.metaValue}>{rec.walking_minutes} min walk</Text>
                  </View>
                )}
                {rec.scooter_minutes != null && (
                  <View style={styles.metaPill}>
                    <FontAwesome name="bolt" size={12} color={Colors.light.textSecondary} />
                    <Text style={styles.metaValue}>{rec.scooter_minutes} min scooter</Text>
                  </View>
                )}
                {price && (
                  <View style={styles.metaPill}>
                    <Text style={styles.metaValue}>{price}</Text>
                  </View>
                )}
              </View>

              <View style={styles.macros}>
                <MacroPill label="Cal" value={rec.calories} unit="" highlight />
                <MacroPill label="Protein" value={rec.protein_g} unit="g" />
                <MacroPill label="Carbs" value={rec.total_carbs_g} unit="g" />
                <MacroPill label="Fat" value={rec.total_fat_g} unit="g" />
              </View>

              {rec.reason ? (
                <View style={styles.reasonRow}>
                  <FontAwesome name="lightbulb-o" size={13} color={Colors.gold} />
                  <Text style={styles.reason}>{rec.reason}</Text>
                </View>
              ) : null}

              {rec.latitude != null && rec.longitude != null && (
                <Pressable
                  style={({ pressed }) => [
                    styles.goButton,
                    pressed && { opacity: 0.85, transform: [{ scale: 0.98 }] },
                  ]}
                  onPress={() => handleGoNow(rec.latitude!, rec.longitude!, rec.dining_hall)}
                >
                  <FontAwesome name="location-arrow" size={14} color="#FFFFFF" />
                  <Text style={styles.goButtonText}>Go Now</Text>
                </Pressable>
              )}
            </View>
          );
        })}
      </ScrollView>
    </View>
  );
}

function MacroPill({
  label,
  value,
  unit,
  highlight,
}: {
  label: string;
  value: number | null;
  unit: string;
  highlight?: boolean;
}) {
  if (value == null) return null;
  return (
    <View style={styles.macroPill}>
      <Text style={[styles.macroValue, highlight && { color: Colors.gold }]}>
        {Math.round(value)}{unit}
      </Text>
      <Text style={styles.macroLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { flex: 1, backgroundColor: Colors.light.background },
  container: { flex: 1 },
  content: { padding: 20, paddingBottom: 40 },

  closeButton: {
    position: "absolute",
    top: 12,
    right: 16,
    zIndex: 10,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.light.card,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: Colors.light.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },

  header: {
    fontSize: 26,
    fontWeight: "800",
    color: Colors.navy,
    marginBottom: 4,
  },
  subheader: {
    fontSize: 14,
    color: Colors.light.textSecondary,
    marginBottom: 20,
  },

  card: {
    backgroundColor: Colors.light.card,
    borderRadius: 18,
    padding: 18,
    marginBottom: 14,
    shadowColor: Colors.light.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 10,
    elevation: 2,
  },
  cardTop: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    marginBottom: 12,
  },
  rankBadge: {
    width: 32,
    height: 32,
    borderRadius: 10,
    backgroundColor: Colors.navy,
    alignItems: "center",
    justifyContent: "center",
  },
  rankText: { color: Colors.gold, fontWeight: "800", fontSize: 15 },
  titleBlock: { flex: 1 },
  foodName: {
    fontSize: 17,
    fontWeight: "700",
    color: Colors.navy,
    lineHeight: 22,
  },
  locationRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 3,
  },
  location: {
    fontSize: 13,
    color: Colors.light.textSecondary,
  },

  metaRow: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 12,
  },
  metaPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    backgroundColor: Colors.light.input,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  metaValue: {
    fontSize: 13,
    fontWeight: "600",
    color: Colors.light.textSecondary,
  },

  macros: {
    flexDirection: "row",
    gap: 6,
    marginBottom: 10,
  },
  macroPill: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: Colors.light.input,
  },
  macroValue: {
    fontSize: 15,
    fontWeight: "700",
    color: Colors.navy,
  },
  macroLabel: {
    fontSize: 10,
    color: Colors.light.textSecondary,
    marginTop: 2,
    fontWeight: "600",
  },

  reasonRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
    marginTop: 2,
  },
  reason: {
    flex: 1,
    fontSize: 13,
    color: Colors.light.textSecondary,
    lineHeight: 19,
  },
  goButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: Colors.gold,
    borderRadius: 12,
    paddingVertical: 12,
    marginTop: 12,
  },
  goButtonText: {
    fontSize: 15,
    fontWeight: "700",
    color: "#FFFFFF",
  },

  empty: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 32,
    backgroundColor: Colors.light.background,
  },
  emptyIcon: { fontSize: 48, marginBottom: 16 },
  emptyTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: Colors.navy,
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 15,
    color: Colors.light.textSecondary,
    textAlign: "center",
  },
});
