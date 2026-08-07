// API contract types — mirror the FastAPI response models.

export interface Me {
  email: string;
  display_name: string;
}

export interface LessonSummary {
  slug: string;
  title: string;
  difficulty: string;
  concepts: string[];
  has_quiz: boolean;
  has_exercise: boolean;
}

export interface ModuleInfo {
  id: string;
  number: number;
  stage: number;
  title: string;
  description: string;
  implemented: boolean;
  lessons: LessonSummary[];
}

export interface Curriculum {
  modules: ModuleInfo[];
  challenges: { id: string; title: string; stage: number }[];
}

export interface Lesson {
  slug: string;
  title: string;
  module: string;
  difficulty: string;
  concepts: string[];
  prerequisites: string[];
  quiz: string | null;
  exercise: string | null;
  flashcards: string[];
  body: string;
}

export interface VocabTerm {
  slug: string;
  term: string;
  mental_model: string;
  technical: string;
  why_it_matters: string;
  related: string[];
  module: string;
}

export interface QuizQuestion {
  id: string;
  type: "multiple_choice" | "text";
  prompt: string;
  concepts: string[];
  options: string[] | null;
}

export interface Quiz {
  id: string;
  questions: QuizQuestion[];
}

export interface AnswerResult {
  correct: boolean;
  explanation: string;
  correct_answer: string | number | null;
}

export interface ExerciseInfo {
  id: string;
  title: string;
  mission: string;
  concepts: string[];
  goal_checklist: string[];
  hint_count: number;
}

export interface TranscriptEntry {
  input: string;
  output: string[];
  cwd_after: string;
}

export interface GoalStatus {
  description: string;
  met: boolean;
}

export interface TermState {
  cwd: string;
  transcript: TranscriptEntry[];
  goals: GoalStatus[];
  completed: boolean;
}

export interface ChallengeInfo {
  id: string;
  title: string;
  stage: number;
  briefing: string;
  questions: QuizQuestion[];
  goal_checklist: string[];
}

export interface ChallengeStatus {
  goals_met: boolean;
  questions_total: number;
  questions_correct: number;
  completed: boolean;
  success_text: string | null;
}

export interface Flashcard {
  slug: string;
  front: string;
  back: string;
}

export interface MasteryEvidence {
  achieved?: boolean;
  correct?: number;
  total?: number;
  weight: number;
  earned?: number;
  note?: string;
}

export interface MasteryEntry {
  concept: string;
  term: string;
  score: number;
  breakdown: Record<string, MasteryEvidence>;
  updated_at: string;
}

export interface ModuleProgress {
  id: string;
  title: string;
  stage: number;
  number: number;
  implemented: boolean;
  lessons_total: number;
  lessons_completed: number;
}

export interface Progress {
  modules: ModuleProgress[];
  lessons_started: number;
  lessons_completed: number;
  concepts_tracked: number;
  concepts_mastered: number;
  recently_learned: { concept: string; score: number }[];
  needs_review: { concept: string; score: number }[];
  due_flashcards: number;
  next_lesson: string | null;
  study_minutes_recent: number;
}

export type LessonProgressMap = Record<string, { completed: boolean }>;
