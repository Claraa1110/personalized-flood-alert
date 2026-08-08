// 共用的財產類型定義、圖示、建議文字

export type PropertyType = 'house' | 'car' | 'shop' | 'warehouse' | 'farm' | 'custom';

export const TYPE_ICONS: Record<string, string> = {
  house:     'home',
  car:       'car',
  shop:      'storefront',
  warehouse: 'business',
  farm:      'leaf',
  custom:    'cube',
  other:     'cube', // legacy
};

export const TYPE_LABELS: Record<string, string> = {
  house:     '住家',
  car:       '車輛',
  shop:      '店面',
  warehouse: '倉庫',
  farm:      '農地',
  custom:    '其他',
  other:     '其他', // legacy
};

const ADVICE_TEXTS: Record<'level1' | 'level2', Record<string, string>> = {
  level2: {
    house:     '留意積水，可準備擋水設施，貴重物品移至高處',
    car:       '留意路況，考慮先將車輛移至高處',
    shop:      '留意進水，可準備擋水設施，生財器具、貨物先墊高',
    warehouse: '留意進水，庫存墊高、檢查排水',
    farm:      '留意排水，檢查田間水路是否暢通',
    custom:    '該地區可能有淹水風險，請留意天氣變化',
    other:     '該地區可能有淹水風險，請留意天氣變化',
  },
  level1: {
    house:     '緊急：一樓人員注意安全，切勿進入地下室',
    car:       '緊急：立即移車，地下停車場請盡速駛離',
    shop:      '緊急：關閉電源，人員撤離，遠離淹水區',
    warehouse: '緊急：關閉電源總開關，人員撤離',
    farm:      '緊急：注意人身安全，勿冒險巡田或搶收',
    custom:    '緊急：該地區已達警戒，請注意人身安全並遠離淹水區域',
    other:     '緊急：該地區已達警戒，請注意人身安全並遠離淹水區域',
  },
};

export function getAdviceText(
  level: 'level1' | 'level2',
  type: string,
): string {
  const map = ADVICE_TEXTS[level];
  return map[type] ?? map.custom;
}

export function getAdvice(
  level: 'safe' | 'level2' | 'level1' | null,
  type: string,
): { text: string; bg: string; border: string; icon: string; textColor: string } | null {
  if (!level || level === 'safe') return null;
  const text = getAdviceText(level, type);
  if (level === 'level1') {
    return { text, bg: '#FFF0F0', border: '#FFCCCC', icon: '⚠️', textColor: '#8B0000' };
  }
  return { text, bg: '#FFF5EC', border: '#FFDDB8', icon: '⚠️', textColor: '#7D4000' };
}
