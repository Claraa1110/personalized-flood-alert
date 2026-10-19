import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

interface Props {
  onClose: () => void;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionBody}>{children}</View>
    </View>
  );
}

function Paragraph({ children }: { children: string }) {
  return <Text style={styles.paragraph}>{children}</Text>;
}

function NumberedItem({ n, children }: { n: number; children: string }) {
  return (
    <View style={styles.listItem}>
      <Text style={styles.listBullet}>{n}.</Text>
      <Text style={styles.listText}>{children}</Text>
    </View>
  );
}

function BulletItem({ label, children }: { label: string; children: string }) {
  return (
    <View style={styles.listItem}>
      <Text style={styles.listBullet}>・</Text>
      <Text style={styles.listText}>
        <Text style={styles.listLabel}>{label}</Text>
        {children}
      </Text>
    </View>
  );
}

export default function AboutScreen({ onClose }: Props) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>關於本 App</Text>
        <TouchableOpacity onPress={onClose} style={styles.closeBtn} activeOpacity={0.7}>
          <Ionicons name="close" size={22} color="#555" />
        </TouchableOpacity>
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <Section title="使用說明">
          <Paragraph>「水先知」為你監看所登記財產所在地的淹水風險。</Paragraph>
          <NumberedItem n={1}>
            {'在「列表」頁點右下角「+」新增財產（住家、車輛、店面等），輸入名稱、選類型、設位置。'}
          </NumberedItem>
          <NumberedItem n={2}>
            {'系統持續比對財產所在地的即時雨量與淹水警戒門檻。'}
          </NumberedItem>
          <NumberedItem n={3}>
            {'風險升高時，首頁顯示警示並發送推播通知，提供對應防護建議。'}
          </NumberedItem>
          <NumberedItem n={4}>
            {'可為財產設定重要程度（1–10），多處同時有風險時，首頁依重要程度建議優先處理順序。'}
          </NumberedItem>
          <View style={styles.statusList}>
            <Text style={styles.statusItem}>☀️ 大晴天 — 安全</Text>
            <Text style={styles.statusItem}>⛅ 多雲 — 有降雨但未達警戒</Text>
            <Text style={styles.statusItem}>🌧️ 注意 — 二級預警</Text>
            <Text style={styles.statusItem}>⛈️ 警戒 — 一級警戒</Text>
          </View>
        </Section>

        <Section title="資料來源">
          <Paragraph>本 App 整合下列政府公開資料：</Paragraph>
          <BulletItem label="中央氣象署：">
            {'即時雨量觀測與鄉鎮天氣預報。'}
          </BulletItem>
          <BulletItem label="經濟部水利署：">
            {'各鄉鎮的淹水警戒門檻（1、3、6 小時累積雨量）。'}
          </BulletItem>
          <Paragraph>系統並參考歷史淹水事件，對警戒門檻進行校正，貼近當地實際受災情況。</Paragraph>
        </Section>

        <Section title="免責聲明">
          <Paragraph>
            本 App 提供的淹水預警資訊僅供參考，不代表官方正式警報。實際災害狀況請以中央氣象署、經濟部水利署及各級政府發布的官方警報與指示為準。
          </Paragraph>
          <Paragraph>
            本服務不對預警的準確性、即時性或完整性作任何保證，亦不對因使用或信賴本 App 資訊所導致的任何損失負責。
          </Paragraph>
          <Paragraph>
            遇緊急狀況，請立即撥打相關緊急電話並遵循政府指示。
          </Paragraph>
        </Section>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0F4F8' },

  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    backgroundColor: '#fff', paddingHorizontal: 16, paddingVertical: 14,
    borderBottomWidth: 1, borderBottomColor: '#EAEAEA',
  },
  headerTitle: { fontSize: 17, fontWeight: '700', color: '#1A1A2E' },
  closeBtn: { position: 'absolute', right: 16, padding: 4 },

  content: { padding: 20, paddingBottom: 48, gap: 8 },

  section: {
    backgroundColor: '#fff', borderRadius: 16, padding: 18,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
    gap: 10,
  },
  sectionTitle: {
    fontSize: 13, fontWeight: '700', color: '#2E75B6',
    textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2,
  },
  sectionBody: { gap: 8 },

  paragraph: { fontSize: 14, color: '#444', lineHeight: 22 },

  listItem: { flexDirection: 'row', gap: 6, alignItems: 'flex-start' },
  listBullet: { fontSize: 14, color: '#888', lineHeight: 22, width: 18, flexShrink: 0 },
  listText: { fontSize: 14, color: '#444', lineHeight: 22, flex: 1 },
  listLabel: { fontWeight: '600', color: '#333' },

  statusList: {
    backgroundColor: '#F7F9FC', borderRadius: 10, padding: 12, gap: 6,
  },
  statusItem: { fontSize: 13, color: '#555', lineHeight: 20 },
});
