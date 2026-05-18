const productionProfiles = new Set(["prod", "production"]);

export const simulatorProfile = (import.meta.env.VITE_SIMULATOR_PROFILE ?? "development").trim().toLowerCase();
export const isPublicSimulatorProfile = productionProfiles.has(simulatorProfile);
export const localMonthlyRebalanceEnabled = !isPublicSimulatorProfile;
