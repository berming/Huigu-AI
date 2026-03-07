import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator
} from 'react-native';
import { Colors, Spacing, Radius } from '../../constants/theme';

interface Props {
  url: string;
  onClose?: () => void;
}

export function AIStreamCard({ url, onClose }: Props) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    let aborted = false;
    setText('');
    setLoading(true);
    setError(null);

    const fetchStream = async () => {
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        if (!response.body) throw new Error('No stream body');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (!aborted) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              if (data === '[DONE]') break;
              if (data) {
                setText(prev => prev + data);
                scrollRef.current?.scrollToEnd({ animated: false });
              }
            }
          }
        }
      } catch (e: any) {
        if (!aborted) setError(e?.message ?? 'AI分析暂不可用');
      } finally {
        if (!aborted) setLoading(false);
      }
    };

    fetchStream();
    return () => { aborted = true; };
  }, [url]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.titleRow}>
          <View style={styles.aiDot} />
          <Text style={styles.title}>AI深度分析</Text>
          {loading && <ActivityIndicator size="small" color={Colors.ai.purple} style={{ marginLeft: 8 }} />}
        </View>
        {onClose && (
          <TouchableOpacity onPress={onClose}>
            <Text style={styles.close}>✕</Text>
          </TouchableOpacity>
        )}
      </View>

      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>⚠️ {error}</Text>
          <Text style={styles.errorHint}>请确认后端API已启动并配置ANTHROPIC_API_KEY</Text>
        </View>
      ) : (
        <ScrollView ref={scrollRef} style={styles.scroll} showsVerticalScrollIndicator={false}>
          <Text style={styles.analysisText}>
            {text || (loading ? '正在生成AI分析...' : '')}
          </Text>
          {loading && !text && (
            <View style={styles.skeleton}>
              {[0.9, 0.7, 0.85, 0.6].map((w, i) => (
                <View key={i} style={[styles.skeletonLine, { width: `${w * 100}%` }]} />
              ))}
            </View>
          )}
        </ScrollView>
      )}

      <Text style={styles.disclaimer}>
        AI生成内容，仅供参考，不构成投资建议
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bg.card,
    borderRadius: Radius.lg,
    marginHorizontal: Spacing.lg,
    marginVertical: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.ai.purple + '40',
    overflow: 'hidden',
    maxHeight: 400,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.bg.border,
    backgroundColor: Colors.bg.elevated,
  },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  aiDot: {
    width: 8, height: 8, borderRadius: 4,
    backgroundColor: Colors.ai.purple,
  },
  title: { color: Colors.text.primary, fontSize: 14, fontWeight: '700' },
  close: { color: Colors.text.secondary, fontSize: 16, padding: 4 },
  scroll: { padding: Spacing.md, maxHeight: 320 },
  analysisText: {
    color: Colors.text.secondary,
    fontSize: 13,
    lineHeight: 22,
  },
  skeleton: { gap: 8, paddingVertical: Spacing.md },
  skeletonLine: {
    height: 12,
    backgroundColor: Colors.bg.elevated,
    borderRadius: Radius.sm,
  },
  errorBox: {
    padding: Spacing.lg,
    alignItems: 'center',
    gap: Spacing.sm,
  },
  errorText: { color: Colors.risk, fontSize: 13, textAlign: 'center' },
  errorHint: { color: Colors.text.muted, fontSize: 11, textAlign: 'center' },
  disclaimer: {
    color: Colors.text.muted,
    fontSize: 10,
    textAlign: 'center',
    paddingVertical: Spacing.sm,
    borderTopWidth: 1,
    borderTopColor: Colors.bg.border,
  },
});
