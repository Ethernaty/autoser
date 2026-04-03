export type LandingIcon =
  | "users"
  | "car"
  | "clipboard"
  | "userCog"
  | "calculator"
  | "history"
  | "alert"
  | "clock"
  | "gauge"
  | "monitor"
  | "wallet"
  | "wrench"
  | "shield"
  | "fileText";

export const landingContent = {
  brand: {
    name: "AutoService CRM",
    tagline: "CRM для СТО и автосервисов"
  },
  navigation: [
    { label: "Проблемы", href: "#pain" },
    { label: "Решение", href: "#solution" },
    { label: "Возможности", href: "#features" },
    { label: "Как это работает", href: "#workflow" },
    { label: "FAQ", href: "#faq" }
  ],
  cta: {
    label: "Оставить заявку",
    href: "#request-contact",
    secondaryLabel: "Войти"
  },
  hero: {
    title: "CRM для автосервиса: приёмка, заказ-наряды и контроль команды в одном окне",
    subtitle:
      "Работайте в браузере без Excel и чатов: фиксируйте обращения, ведите заказ-наряды и держите статус каждого авто под контролем.",
    proofPoints: [
      "Клиент, автомобиль и история работ в одной карточке",
      "Единый поток: приёмка → работа → выдача без дублирования",
      "Владелец, администратор и мастер видят одни и те же статусы"
    ],
    trustBadges: [
      "Без установки и локальных серверов",
      "Запуск по вашим рабочим сценариям",
      "Контроль заказов и выплат в одной системе"
    ],
    preview: {
      kpis: [
        { label: "Открытые заказ-наряды", value: "12" },
        { label: "Авто в работе", value: "7" },
        { label: "К выдаче сегодня", value: "3" }
      ],
      activeOrders: [
        { code: "WO-2481", client: "Клиент: Иванов Д.", car: "Kia Rio А247МР", status: "in_progress" },
        { code: "WO-2482", client: "Клиент: ООО Транзит", car: "Ford Transit В901КТ", status: "new" },
        { code: "WO-2478", client: "Клиент: Петров А.", car: "Skoda Octavia К412ХР", status: "ready" }
      ]
    }
  },
  pain: {
    title: "Что обычно тормозит работу СТО",
    subtitle: "Когда процессы разбросаны по чатам и таблицам, сервис теряет скорость и управляемость.",
    items: [
      {
        icon: "alert" as const,
        title: "Карточки клиентов и авто разрознены",
        description: "Информация разбросана по чатам, заметкам и Excel."
      },
      {
        icon: "fileText" as const,
        title: "История ремонта теряется",
        description: "Нельзя быстро понять, что уже делали по машине."
      },
      {
        icon: "clock" as const,
        title: "Приёмка занимает лишнее время",
        description: "Много ручного ввода и повторяющихся действий."
      },
      {
        icon: "users" as const,
        title: "Непрозрачная загрузка сотрудников",
        description: "Сложно видеть занятость и фактическую выработку."
      },
      {
        icon: "calculator" as const,
        title: "Расчёт зарплаты вызывает споры",
        description: "Нет единого и понятного источника по выплатам."
      },
      {
        icon: "gauge" as const,
        title: "Нет общей картины по статусам",
        description: "Трудно быстро увидеть, что в работе, задержано и готово."
      }
    ]
  },
  solution: {
    title: "AutoService CRM упрощает ежедневную работу сервиса",
    subtitle: "Один рабочий контур для приёмки, статусов, команды и выплат без переключений между инструментами.",
    pillars: [
      {
        icon: "monitor" as const,
        title: "Одна браузерная система",
        description: "Работа из любой точки без установки и сложной инфраструктуры."
      },
      {
        icon: "clipboard" as const,
        title: "Понятный ежедневный поток",
        description: "От приёмки до закрытия заказа по единому сценарию."
      },
      {
        icon: "shield" as const,
        title: "Прозрачность для владельца",
        description: "Статусы и исполнители видны без ручной сверки."
      }
    ]
  },
  features: {
    title: "Ключевые возможности автосервиса",
    items: [
      {
        icon: "users" as const,
        title: "Клиенты",
        description: "Единая база клиентов с контактами и историей."
      },
      {
        icon: "car" as const,
        title: "Автомобили",
        description: "Учет авто: марка, номер, VIN, история обслуживания."
      },
      {
        icon: "clipboard" as const,
        title: "Заказ-наряды",
        description: "Создание и контроль заказ-нарядов по понятным статусам."
      },
      {
        icon: "userCog" as const,
        title: "Сотрудники",
        description: "Назначение исполнителей и прозрачная загрузка команды."
      },
      {
        icon: "calculator" as const,
        title: "Расчёт зарплаты",
        description: "Выплаты на основе выполненных работ, без ручных таблиц."
      },
      {
        icon: "history" as const,
        title: "История и контроль",
        description: "История клиента, авто и заказов всегда под рукой."
      }
    ]
  },
  workflow: {
    title: "Как это работает каждый день",
    steps: [
      {
        step: "01",
        title: "Приём клиента и автомобиля",
        description: "Находите клиента, фиксируете авто и запрос."
      },
      {
        step: "02",
        title: "Оформление заказ-наряда",
        description: "Создаёте заказ-наряд и назначаете исполнителя."
      },
      {
        step: "03",
        title: "Контроль выполнения",
        description: "Отслеживаете статус и прогресс по каждому заказу."
      },
      {
        step: "04",
        title: "Прозрачное завершение",
        description: "Закрываете заказ, фиксируете итог и сохраняете историю."
      },
      {
        step: "05",
        title: "Расчёт выплат сотрудникам",
        description: "Рассчитываете выплаты по фактической выработке."
      }
    ]
  },
  benefits: {
    title: "Что получает сервис",
    items: [
      {
        icon: "gauge" as const,
        title: "Меньше операционного хаоса",
        description: "Один источник данных вместо разрозненных заметок."
      },
      {
        icon: "clock" as const,
        title: "Быстрее приёмка и оформление",
        description: "Меньше рутины при создании и ведении заказов."
      },
      {
        icon: "history" as const,
        title: "Меньше потерянных деталей",
        description: "История по клиенту и авто не теряется между сменами."
      },
      {
        icon: "users" as const,
        title: "Лучший контроль команды",
        description: "Понятно, кто выполняет работу и где перегруз."
      },
      {
        icon: "wallet" as const,
        title: "Прозрачный расчёт выплат",
        description: "Выплаты опираются на фактические выполненные работы."
      }
    ]
  },
  preview: {
    title: "Реальные рабочие экраны",
    subtitle: "Интерфейс собран под ежедневные операции сервиса: от приёмки до контроля выплат.",
    cards: [
      {
        title: "Карточка клиента",
        label: "Клиент + контакты",
        rows: [
          { name: "Клиент", value: "Иванов Дмитрий" },
          { name: "Телефон", value: "+7 (900) 321-44-55" },
          { name: "Автомобили", value: "2 активных" },
          { name: "Последний визит", value: "12.03.2026" }
        ]
      },
      {
        title: "История автомобиля",
        label: "История работ",
        rows: [
          { name: "Kia Rio А247МР", value: "ТО-2 + колодки" },
          { name: "06.03.2026", value: "Заказ-наряд WO-2468" },
          { name: "17.02.2026", value: "Диагностика подвески" },
          { name: "29.01.2026", value: "Замена масла и фильтров" }
        ]
      },
      {
        title: "Заказ-наряд",
        label: "Статус и контроль",
        rows: [
          { name: "Номер", value: "WO-2481" },
          { name: "Статус", value: "В работе" },
          { name: "Исполнитель", value: "Павел Власов" },
          { name: "Сумма", value: "18 500 ₽" }
        ]
      },
      {
        title: "Сотрудники и зарплата",
        label: "Расчёт выплат",
        rows: [
          { name: "Сергей К.", value: "9 заказов / 42 700 ₽" },
          { name: "Павел В.", value: "11 заказов / 48 900 ₽" },
          { name: "Игорь Т.", value: "7 заказов / 33 100 ₽" },
          { name: "Период", value: "01.03 — 31.03" }
        ]
      }
    ]
  },
  audience: {
    title: "Кому подходит AutoService CRM",
    items: [
      {
        icon: "wrench" as const,
        title: "Небольшие СТО",
        description: "Когда нужна понятная система вместо таблиц и чатов."
      },
      {
        icon: "gauge" as const,
        title: "Растущие сервисы",
        description: "Когда важно сохранить порядок при росте потока авто."
      },
      {
        icon: "shield" as const,
        title: "Сервисы с владельцем в операционке",
        description: "Когда нужен быстрый контроль статусов и загрузки."
      },
      {
        icon: "userCog" as const,
        title: "Администраторы и менеджеры",
        description: "Когда нужна быстрая приёмка и чёткая история."
      }
    ]
  },
  faq: {
    title: "Частые вопросы",
    items: [
      {
        question: "Нужна ли установка программы на компьютеры?",
        answer: "Нет. AutoService CRM работает в браузере, поэтому отдельная установка не требуется."
      },
      {
        question: "Можно ли работать с системой из разных точек?",
        answer: "Да. Можно работать из офиса, приёмки и сервисной зоны."
      },
      {
        question: "Подойдёт ли решение для небольшого автосервиса?",
        answer: "Да. Система рассчитана на небольшие и средние СТО."
      },
      {
        question: "Какие данные хранятся в системе?",
        answer: "Клиенты, автомобили, заказ-наряды, статусы и данные по сотрудникам."
      }
    ]
  },
  finalCta: {
    title: "Оставьте заявку и посмотрите AutoService CRM на вашем процессе",
    subtitle: "Покажем ключевые экраны на типовых задачах вашего сервиса и дадим понятный план внедрения.",
    contactNote: "Без выдуманных кейсов: на встрече разбираем ваш реальный сценарий работы.",
    contacts: [
      { label: "Формат встречи", value: "30–40 минут в браузере", href: "#request-contact" },
      { label: "Что подготовить", value: "2–3 типовых заказа и роли команды", href: "#workflow" },
      { label: "После встречи", value: "Пошаговый план запуска на 7 дней", href: "#benefits" }
    ]
  }
} as const;

export const landingVisualData = {
  heroTrend: [
    { name: "Пн", orders: 8 },
    { name: "Вт", orders: 11 },
    { name: "Ср", orders: 9 },
    { name: "Чт", orders: 14 },
    { name: "Пт", orders: 13 },
    { name: "Сб", orders: 10 }
  ],
  statusDistribution: [
    { name: "Новые", value: 5, color: "hsl(var(--primary))" },
    { name: "В работе", value: 7, color: "hsl(var(--warning))" },
    { name: "Готово", value: 4, color: "hsl(var(--success))" }
  ],
  payrollBars: [
    { name: "Сергей", payout: 42.7 },
    { name: "Павел", payout: 48.9 },
    { name: "Игорь", payout: 33.1 },
    { name: "Андрей", payout: 36.4 }
  ],
  returnDynamics: [
    { name: "Янв", value: 14 },
    { name: "Фев", value: 18 },
    { name: "Мар", value: 21 },
    { name: "Апр", value: 19 },
    { name: "Май", value: 24 },
    { name: "Июн", value: 27 }
  ],
  orderFlow: [
    { step: "Приёмка", value: 16 },
    { step: "Диагностика", value: 13 },
    { step: "Ремонт", value: 9 },
    { step: "Контроль", value: 6 },
    { step: "Выдача", value: 5 }
  ]
} as const;
