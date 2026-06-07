// API contract types — keep in sync with backend Pydantic models
// 最后同步：docs/api-contract.md 3.1-3.3 节

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
  location: string;
  time_of_day: string;
  source_chapter: number;
  characters: string[];
  elements: SceneElement[];
}

export interface Screenplay {
  id: string;
  novel_id: string;
  title: string;
  source_novel: string;
  novel_author: string;
  total_chapters: number;
  generated_by: string;
  scenes: Scene[];
}

// --- CPC 因果图类型 ---

export type RelationType = "causes" | "before" | "references";

export interface Event {
  id: string;
  index: number;
  chapter_index: number;
  description: string;
  characters: string[];
  location: string;
  time: string;
}

export interface CausalRelation {
  id: string;
  source_event_id: string;
  target_event_id: string;
  relation_type: RelationType;
  confidence: number;
}

export interface CausalGraph {
  id: string;
  novel_id: string;
  events: Event[];
  relations: CausalRelation[];
  dag_valid: boolean;
  created_at: string;
}
