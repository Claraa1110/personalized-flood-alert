import { View, Text, TextInput, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { PropertyType } from '../lib/advice';

const MAIN_BTNS = [
  { key: 'house' as PropertyType, label: '住家', icon: 'home-outline'       },
  { key: 'car'   as PropertyType, label: '車輛', icon: 'car-outline'        },
  { key: 'shop'  as PropertyType, label: '店面', icon: 'storefront-outline' },
] as const;

const SUB_BTNS = [
  { key: 'warehouse' as PropertyType, label: '倉庫',     icon: 'business-outline' },
  { key: 'farm'      as PropertyType, label: '農地',     icon: 'leaf-outline'     },
  { key: 'custom'    as PropertyType, label: '自行輸入', icon: 'create-outline'   },
] as const;

const OTHER_SUBTYPES = new Set<string>(['warehouse', 'farm', 'custom', 'other']);

interface Props {
  value: PropertyType;
  onChange: (type: PropertyType) => void;
  customTypeName: string;
  onCustomTypeNameChange: (name: string) => void;
}

export default function TypeSelector({ value, onChange, customTypeName, onCustomTypeNameChange }: Props) {
  const isOtherGroup = OTHER_SUBTYPES.has(value);

  return (
    <View>
      {/* 主類型（4 個按鈕） */}
      <View style={styles.row}>
        {MAIN_BTNS.map((opt) => {
          const active = value === opt.key;
          return (
            <TouchableOpacity
              key={opt.key}
              style={[styles.btn, active && styles.btnActive]}
              onPress={() => onChange(opt.key)}
              activeOpacity={0.7}
            >
              <Ionicons name={opt.icon as any} size={22} color={active ? '#2E75B6' : '#aaa'} />
              <Text style={[styles.label, active && styles.labelActive]}>{opt.label}</Text>
            </TouchableOpacity>
          );
        })}

        {/* 其他（群組按鈕） */}
        <TouchableOpacity
          style={[styles.btn, isOtherGroup && styles.btnActive]}
          onPress={() => { if (!isOtherGroup) onChange('warehouse'); }}
          activeOpacity={0.7}
        >
          <Ionicons name="apps-outline" size={22} color={isOtherGroup ? '#2E75B6' : '#aaa'} />
          <Text style={[styles.label, isOtherGroup && styles.labelActive]}>其他</Text>
        </TouchableOpacity>
      </View>

      {/* 其他 子類型 */}
      {isOtherGroup && (
        <View style={styles.subRow}>
          {SUB_BTNS.map((opt) => {
            const active = value === opt.key;
            return (
              <TouchableOpacity
                key={opt.key}
                style={[styles.subBtn, active && styles.subBtnActive]}
                onPress={() => onChange(opt.key)}
                activeOpacity={0.7}
              >
                <Ionicons name={opt.icon as any} size={15} color={active ? '#2E75B6' : '#999'} />
                <Text style={[styles.subLabel, active && styles.subLabelActive]}>{opt.label}</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      )}

      {/* 自行輸入文字框 */}
      {value === 'custom' && (
        <TextInput
          style={styles.customInput}
          placeholder="請輸入類型（如：廠房、工作室）"
          placeholderTextColor="#bbb"
          value={customTypeName}
          onChangeText={onCustomTypeNameChange}
          maxLength={30}
          returnKeyType="done"
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 8 },

  btn: {
    flex: 1, alignItems: 'center', justifyContent: 'center', gap: 5,
    paddingVertical: 12, borderRadius: 12, borderWidth: 1.5,
    borderColor: '#E0E0E0', backgroundColor: '#fff',
  },
  btnActive: { borderColor: '#2E75B6', backgroundColor: '#EBF3FB' },
  label: { fontSize: 11, color: '#aaa', fontWeight: '600' },
  labelActive: { color: '#2E75B6' },

  subRow: {
    flexDirection: 'row', gap: 8, marginTop: 8,
    paddingLeft: 4,
  },
  subBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 5,
    paddingVertical: 9, borderRadius: 10, borderWidth: 1.5,
    borderColor: '#E0E0E0', backgroundColor: '#FAFAFA',
  },
  subBtnActive: { borderColor: '#2E75B6', backgroundColor: '#EBF3FB' },
  subLabel: { fontSize: 12, color: '#999', fontWeight: '600' },
  subLabelActive: { color: '#2E75B6' },

  customInput: {
    marginTop: 8, borderWidth: 1.5, borderColor: '#2E75B6', borderRadius: 10,
    paddingHorizontal: 14, paddingVertical: 10, fontSize: 14, color: '#222',
    backgroundColor: '#F5F9FE',
  },
});
