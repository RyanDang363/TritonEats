import { useEffect, useState } from "react";
import {
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useRouter } from "expo-router";
import { useAuth } from "@/context/AuthContext";
import { supabase } from "@/lib/supabase";
import Colors from "@/constants/Colors";

interface Profile {
  fitness_goal: string;
  allergies: string[];
  diet_restrictions: string[];
}

function SettingsRow({
  icon,
  label,
  value,
  onPress,
  destructive,
}: {
  icon: React.ComponentProps<typeof FontAwesome>["name"];
  label: string;
  value?: string;
  onPress: () => void;
  destructive?: boolean;
}) {
  return (
    <Pressable
      style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
      onPress={onPress}
    >
      <View style={[styles.rowIcon, destructive && { backgroundColor: "#FEE2E2" }]}>
        <FontAwesome
          name={icon}
          size={16}
          color={destructive ? "#DC2626" : Colors.navy}
        />
      </View>
      <View style={styles.rowContent}>
        <Text style={[styles.rowLabel, destructive && { color: "#DC2626" }]}>
          {label}
        </Text>
        {value ? <Text style={styles.rowValue}>{value}</Text> : null}
      </View>
      <FontAwesome name="chevron-right" size={12} color={Colors.light.textTertiary} />
    </Pressable>
  );
}

export default function ProfileScreen() {
  const { user, signOut, resetProfileFlag } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    supabase
      .from("user_profiles")
      .select("fitness_goal, allergies, diet_restrictions")
      .eq("id", user.id)
      .single()
      .then(({ data }: { data: Profile | null }) => {
        if (data) setProfile(data);
      });
  }, [user]);

  const goalLabels: Record<string, string> = {
    cut: "Cutting",
    bulk: "Bulking",
    maintain: "Maintaining",
  };

  const handleChangePassword = async () => {
    if (!newPassword || !confirmPassword) {
      Alert.alert("Error", "Please fill in both fields");
      return;
    }
    if (newPassword.length < 6) {
      Alert.alert("Error", "Password must be at least 6 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      Alert.alert("Error", "Passwords don't match");
      return;
    }
    setSaving(true);
    try {
      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) throw error;
      setShowPasswordModal(false);
      setNewPassword("");
      setConfirmPassword("");
      Alert.alert("Done", "Your password has been updated.");
    } catch (e: any) {
      Alert.alert("Error", e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleChangePreferences = () => {
    if (!user) return;
    resetProfileFlag();
    router.replace("/(survey)/allergies");
  };

  const handleSignOut = () => {
    Alert.alert("Sign Out", "Are you sure?", [
      { text: "Cancel", style: "cancel" },
      { text: "Sign Out", style: "destructive", onPress: signOut },
    ]);
  };

  return (
    <>
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        <View style={styles.avatarSection}>
          <View style={styles.avatar}>
            <FontAwesome name="user" size={28} color={Colors.gold} />
          </View>
          <Text style={styles.email}>{user?.email}</Text>
        </View>

        {profile && (
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>My Preferences</Text>
            <View style={styles.prefRow}>
              <Text style={styles.prefLabel}>Goal</Text>
              <View style={styles.prefBadge}>
                <Text style={styles.prefBadgeText}>
                  {goalLabels[profile.fitness_goal] || profile.fitness_goal}
                </Text>
              </View>
            </View>
            <View style={styles.prefRow}>
              <Text style={styles.prefLabel}>Allergies</Text>
              <Text style={styles.prefValue}>
                {profile.allergies.length > 0 ? profile.allergies.join(", ") : "None"}
              </Text>
            </View>
            <View style={styles.prefRow}>
              <Text style={styles.prefLabel}>Diet</Text>
              <Text style={styles.prefValue}>
                {profile.diet_restrictions.length > 0 ? profile.diet_restrictions.join(", ") : "None"}
              </Text>
            </View>
          </View>
        )}

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Settings</Text>
          <SettingsRow
            icon="refresh"
            label="Change Preferences"
            value="Retake the survey"
            onPress={handleChangePreferences}
          />
          <View style={styles.divider} />
          <SettingsRow
            icon="lock"
            label="Change Password"
            onPress={() => setShowPasswordModal(true)}
          />
          <View style={styles.divider} />
          <SettingsRow
            icon="sign-out"
            label="Sign Out"
            onPress={handleSignOut}
            destructive
          />
        </View>
      </ScrollView>

      <Modal
        visible={showPasswordModal}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setShowPasswordModal(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Change Password</Text>
            <Pressable onPress={() => setShowPasswordModal(false)}>
              <FontAwesome name="times" size={22} color={Colors.light.textSecondary} />
            </Pressable>
          </View>

          <TextInput
            style={styles.modalInput}
            placeholder="New password"
            placeholderTextColor={Colors.light.textTertiary}
            secureTextEntry
            value={newPassword}
            onChangeText={setNewPassword}
          />
          <TextInput
            style={styles.modalInput}
            placeholder="Confirm new password"
            placeholderTextColor={Colors.light.textTertiary}
            secureTextEntry
            value={confirmPassword}
            onChangeText={setConfirmPassword}
          />

          <Pressable
            style={({ pressed }) => [
              styles.modalButton,
              saving && { opacity: 0.55 },
              pressed && { opacity: 0.92 },
            ]}
            onPress={handleChangePassword}
            disabled={saving}
          >
            <Text style={styles.modalButtonText}>
              {saving ? "Updating..." : "Update Password"}
            </Text>
          </Pressable>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.light.background },
  content: { paddingHorizontal: 16, paddingBottom: 120, paddingTop: 12 },

  avatarSection: {
    alignItems: "center",
    marginBottom: 24,
    marginTop: 8,
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: Colors.navy,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  email: {
    fontSize: 15,
    color: Colors.light.textSecondary,
    fontWeight: "500",
  },

  card: {
    backgroundColor: Colors.light.card,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: Colors.light.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: Colors.light.textSecondary,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 14,
  },

  prefRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 8,
  },
  prefLabel: {
    fontSize: 15,
    color: Colors.light.textSecondary,
    fontWeight: "500",
  },
  prefBadge: {
    backgroundColor: Colors.navy,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  prefBadgeText: {
    color: "#FFFFFF",
    fontSize: 13,
    fontWeight: "700",
  },
  prefValue: {
    fontSize: 14,
    color: Colors.navy,
    fontWeight: "600",
    flexShrink: 1,
    textAlign: "right",
    maxWidth: "60%" as any,
  },

  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    gap: 12,
  },
  rowIcon: {
    width: 34,
    height: 34,
    borderRadius: 10,
    backgroundColor: Colors.light.input,
    alignItems: "center",
    justifyContent: "center",
  },
  rowContent: { flex: 1 },
  rowLabel: {
    fontSize: 15,
    fontWeight: "600",
    color: Colors.navy,
  },
  rowValue: {
    fontSize: 12,
    color: Colors.light.textSecondary,
    marginTop: 1,
  },
  divider: {
    height: 1,
    backgroundColor: Colors.light.divider,
    marginLeft: 46,
  },

  modalContainer: {
    flex: 1,
    backgroundColor: Colors.light.background,
    paddingHorizontal: 24,
    paddingTop: 24,
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 32,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: "800",
    color: Colors.navy,
  },
  modalInput: {
    backgroundColor: Colors.light.input,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 15,
    fontSize: 16,
    marginBottom: 12,
    color: Colors.light.text,
  },
  modalButton: {
    backgroundColor: Colors.gold,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 8,
  },
  modalButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
});
