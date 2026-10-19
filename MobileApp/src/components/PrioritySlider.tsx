import { useState, useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Slider from '@react-native-community/slider';

interface Props {
  value: number;
  onChange: (v: number) => void;
}

export default function PrioritySlider({ value, onChange }: Props) {
  const [displayValue, setDisplayValue] = useState(value);

  // 父層傳入的 value 改變時（例如切換編輯不同財產），同步顯示值
  useEffect(() => { setDisplayValue(value); }, [value]);

  return (
    <View style={styles.container}>
      <View style={styles.valueRow}>
        <Text style={styles.label}>低</Text>
        <View style={styles.valueBadge}>
          <Text style={styles.valueText}>{displayValue}</Text>
        </View>
        <Text style={styles.label}>高</Text>
      </View>
      <Slider
        style={styles.slider}
        minimumValue={1}
        maximumValue={10}
        step={1}
        value={value}
        onValueChange={setDisplayValue}
        onSlidingComplete={onChange}
        minimumTrackTintColor="#2E75B6"
        maximumTrackTintColor="#E0E0E0"
        thumbTintColor="#2E75B6"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: 4 },
  valueRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 12,
  },
  label: { fontSize: 13, color: '#999', fontWeight: '600' },
  valueBadge: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: '#2E75B6', alignItems: 'center', justifyContent: 'center',
  },
  valueText: { fontSize: 16, fontWeight: '700', color: '#fff' },
  slider: { width: '100%', height: 40 },
});
