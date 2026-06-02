import { IAgentRuntime } from "@elizaos/core";
import { z } from "zod";

export const siguiEnvSchema = z.object({
    SIGUI_API_URL: z.string().url().default("https://api.sigui.io"),
    SIGUI_API_KEY: z.string().optional(),
});

export type SiguiConfig = z.infer<typeof siguiEnvSchema>;

export async function validateSiguiConfig(
    runtime: IAgentRuntime
): Promise<SiguiConfig> {
    try {
        const config = {
            SIGUI_API_URL: runtime.getSetting("SIGUI_API_URL") || process.env.SIGUI_API_URL,
            SIGUI_API_KEY: runtime.getSetting("SIGUI_API_KEY") || process.env.SIGUI_API_KEY,
        };

        return siguiEnvSchema.parse(config);
    } catch (error) {
        if (error instanceof z.ZodError) {
            const errorMessages = error.errors
                .map((err) => `${err.path.join(".")}: ${err.message}`)
                .join("\n");
            throw new Error(
                `Sigui Protocol configuration validation failed:\n${errorMessages}`
            );
        }
        throw error;
    }
}
