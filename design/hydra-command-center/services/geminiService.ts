import { GoogleGenAI, Type } from "@google/genai";
import { Agent, Project } from "../types";

// Initialize the client defensively
let ai: GoogleGenAI | null = null;
if (process.env.API_KEY) {
  ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
}

export const getGeminiClient = () => ai;

export interface GeminiResponse {
  text: string;
  images?: { data: string; mimeType: string }[];
}

export const sendMessageToGemini = async (
  message: string, 
  systemInstruction?: string,
  imageAttachment?: { data: string; mimeType: string }
): Promise<GeminiResponse> => {
  if (!ai) {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          text: `[SIMULATED] I received your command: "${message}". Since no API key is configured, I am simulating a response.`
        });
      }, 1000);
    });
  }

  try {
    const contents: any = { parts: [] };
    
    // Add text prompt
    if (message) {
      contents.parts.push({ text: message });
    }
    
    // Add image if present
    if (imageAttachment) {
      contents.parts.push({
        inlineData: {
          mimeType: imageAttachment.mimeType,
          data: imageAttachment.data
        }
      });
    }

    const response = await ai.models.generateContent({
      model: imageAttachment ? 'gemini-2.5-flash-image' : 'gemini-2.5-flash',
      contents: contents, 
      config: {
        systemInstruction: systemInstruction || "You are HYDRA, a command center AI. You are concise, technical, and helpful.",
      }
    });

    // Parse response for text and images
    let text = "";
    const images: { data: string; mimeType: string }[] = [];

    if (response.candidates?.[0]?.content?.parts) {
      for (const part of response.candidates[0].content.parts) {
        if (part.text) {
          text += part.text;
        }
        if (part.inlineData) {
          images.push({
            data: part.inlineData.data,
            mimeType: part.inlineData.mimeType
          });
        }
      }
    }
    
    // Fallback if SDK returns text directly on object
    if (!text && response.text) {
        text = response.text;
    }

    return { text, images: images.length > 0 ? images : undefined };

  } catch (error) {
    console.error("Gemini API Error:", error);
    return { text: "Error communicating with HYDRA core." };
  }
};

export const generateAsset = async (prompt: string, type: 'character' | 'scene' = 'character'): Promise<string | null> => {
   if (!ai) return null;

   try {
     const response = await ai.models.generateContent({
       model: 'gemini-2.5-flash-image', 
       contents: {
         parts: [{ text: `Generate a high-quality ${type === 'character' ? 'character portrait' : 'environmental scene'} concept art for: ${prompt}. Sci-fi, Cyberpunk, Cinematic lighting.` }]
       }
     });

     for (const part of response.candidates?.[0]?.content?.parts || []) {
       if (part.inlineData) {
         return `data:${part.inlineData.mimeType};base64,${part.inlineData.data}`;
       }
     }
     return null;
   } catch (e) {
     console.error("Asset Gen Error:", e);
     return null;
   }
}

// --- NEW FEATURES ---

export const simulateAgentThought = async (agent: Agent): Promise<string> => {
  if (!ai) {
    const fallbacks = ["Processing data stream...", "Optimizing neural weights...", "Syncing with swarm...", "Analysing input vector..."];
    return fallbacks[Math.floor(Math.random() * fallbacks.length)];
  }

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: {
        parts: [{ text: `Generate a single, short, technical log entry (max 10 words) representing your current thought process while working on the task: "${agent.task}". Do not use markdown.` }]
      },
      config: {
        systemInstruction: agent.config?.systemInstruction || "You are a cybernetic AI agent. Speak in technical, clipped log format.",
        temperature: 1.0, // High temp for variety
        maxOutputTokens: 20,
      }
    });
    return response.text ? response.text.trim() : "Calculating...";
  } catch (e) {
    return "Connection interrupted...";
  }
};

export const generateProjectTasks = async (project: Project, availableAgents: Agent[]): Promise<any[]> => {
  if (!ai) return [];

  const agentList = availableAgents.map(a => `${a.name} (${a.type})`).join(", ");
  
  try {
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: {
        parts: [{ text: `Project: ${project.name}\nDescription: ${project.description}\n\nGenerate 5 specific technical tasks for this project. Assign each task to the most suitable agent from this list: [${agentList}].` }]
      },
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              title: { type: Type.STRING },
              description: { type: Type.STRING },
              assignee: { type: Type.STRING }
            }
          }
        }
      }
    });
    
    // Ensure we parse the JSON correctly
    const jsonStr = response.text || "[]";
    return JSON.parse(jsonStr);
  } catch (e) {
    console.error("Auto-plan error", e);
    return [];
  }
};