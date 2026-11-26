package com.aura.ai.service;

import com.aura.ai.entity.SettingEntity;
import com.aura.ai.repository.SettingRepository;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class SettingsService {

    private final SettingRepository settingRepository;

    public SettingsService(SettingRepository settingRepository) {
        this.settingRepository = settingRepository;
    }

    @PostConstruct
    public void initDefaults() {
        Map<String, String> defaults = Map.of(
                "web_search_mode", "ask_first",
                "model", "gemma3:1b",
                "theme", "dark",
                "autonomous_repair_limit", "2",
                "research_provider", "bedrock",
                "research_model", "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "research_depth", "standard"
        );

        for (Map.Entry<String, String> entry : defaults.entrySet()) {
            if (!settingRepository.existsById(entry.getKey())) {
                SettingEntity setting = SettingEntity.builder()
                        .key(entry.getKey())
                        .value(entry.getValue())
                        .updatedAt(LocalDateTime.now())
                        .build();
                settingRepository.save(setting);
            }
        }
    }

    public Map<String, String> getSettings() {
        List<SettingEntity> list = settingRepository.findAll();
        Map<String, String> map = new HashMap<>();
        for (SettingEntity s : list) {
            map.put(s.getKey(), s.getValue());
        }
        return map;
    }

    @Transactional
    public Map<String, Object> updateSetting(String key, String value) {
        SettingEntity setting = settingRepository.findById(key).orElseGet(() -> SettingEntity.builder().key(key).build());
        setting.setValue(value);
        setting.setUpdatedAt(LocalDateTime.now());
        settingRepository.save(setting);

        return Map.of("success", true, "key", key, "value", value);
    }

    @Transactional
    public Map<String, Object> updateSettings(Map<String, Object> updates) {
        for (Map.Entry<String, Object> entry : updates.entrySet()) {
            if (entry.getValue() != null) {
                updateSetting(entry.getKey(), String.valueOf(entry.getValue()));
            }
        }
        return Map.of("success", true, "settings", getSettings());
    }
}
