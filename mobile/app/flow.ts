export type ScreenID =
  | "auth"
  | "purchase"
  | "consent"
  | "preparation"
  | "player"
  | "recording"
  | "upload"
  | "results";

export interface ScreenConfig {
  id: ScreenID;
  title: string;
  description: string;
  cta?: string;
  apiEndpoint?: string;
}

export const diagnosticFlow: ScreenConfig[] = [
  {
    id: "auth",
    title: "Войти или создать аккаунт",
    description: "Идентификация родителя для безопасного хранения данных",
    apiEndpoint: "/auth/login",
    cta: "Продолжить",
  },
  {
    id: "purchase",
    title: "Оплатить диагностику",
    description: "Оплата открывает доступ к записи и анализу",
    apiEndpoint: "/billing/checkout",
    cta: "Оплатить",
  },
  {
    id: "consent",
    title: "Согласие на обработку",
    description: "Необходимо юридическое подтверждение перед записью",
    apiEndpoint: "/diagnostics/{sessionId}/consent",
    cta: "Согласен",
  },
  {
    id: "preparation",
    title: "Подготовка пространства",
    description: "Показать инструкции по свету, позе, положению камеры",
    apiEndpoint: "/diagnostics/instructions",
    cta: "Готово",
  },
  {
    id: "player",
    title: "Показать видео",
    description: "Воспроизведение стимула, который должен смотреть ребенок",
  },
  {
    id: "recording",
    title: "Запись камеры",
    description: "Одновременная запись фронтальной камеры и отправка метаданных",
    apiEndpoint: "local://camera",
    cta: "Стоп",
  },
  {
    id: "upload",
    title: "Загрузка видео",
    description: "Фоновая отправка файла на сервер и ожидание результата",
    apiEndpoint: "/diagnostics/{sessionId}/video",
  },
  {
    id: "results",
    title: "Результаты анализа",
    description: "Показать уровень риска, рекомендации и дальнейшие шаги",
    apiEndpoint: "/diagnostics/{sessionId}",
    cta: "Получить консультацию",
  },
];
