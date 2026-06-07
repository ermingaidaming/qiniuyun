// API contract types — keep in sync with backend Pydantic models

export interface Chapter {
  id: string;
  index: number;
  title: string;
  content: string;
  word_count: number;
}

export interface Novel {
  id: string;
  title: string;
  filename: string;
  chapters: Chapter[];
  created_at: string;
}

export type SceneElementType = "action" | "character" | "dialogue" | "parenthetical";

export interface SceneElement {
  type: SceneElementType;
  content: string;
  character: string | null;
}

export interface Scene {
  index: number;
  setting: string;
  elements: SceneElement[];
}

export interface Screenplay {
  id: string;
  novel_id: string;
  title: string;
  scenes: Scene[];
}
