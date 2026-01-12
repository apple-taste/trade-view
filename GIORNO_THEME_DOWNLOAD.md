# 🎵 Giorno's Theme 音频下载指南

## 📥 如何添加真实的JOJO音频

目前系统使用Web Audio API生成的Giorno's Theme旋律，如需使用真实音频文件：

### 方法1：从YouTube下载（推荐）

1. **找到官方音频**：
   - 搜索："Giorno's Theme" 或 "Il vento d'oro"
   - 推荐视频：https://www.youtube.com/watch?v=2MtOpB5LlUA

2. **下载为MP3**：
   - 使用在线工具：https://ytmp3.cc/
   - 或使用youtube-dl：
     ```bash
     youtube-dl -x --audio-format mp3 "视频链接"
     ```

3. **裁剪音频（可选）**：
   - 推荐裁剪前15秒（0:00-0:15）
   - 使用Audacity或在线工具：https://mp3cut.net/

4. **放置文件**：
   ```bash
   cp downloaded-audio.mp3 frontend/public/jojo-alert.mp3
   ```

### 方法2：使用其他JOJO音效

**推荐音效：**
- "To Be Continued" 箭头音效
- "The World" 时停音效
- "Stand Proud" 开场
- "Bloody Stream" 高潮部分

**下载站点：**
- MyInstants: https://www.myinstants.com/search/?name=jojo
- Zedge: https://www.zedge.net/

### 方法3：使用AI生成

使用AI音乐生成器创建JOJO风格音频：
- Suno AI: https://suno.ai/
- Mubert: https://mubert.com/

提示词示例：
```
Create a 10-second epic anime theme song intro 
inspired by JoJo's Bizarre Adventure Golden Wind, 
with dramatic piano melody and energetic rhythm
```

---

## 📁 文件规格

**推荐配置：**
- 格式：MP3
- 时长：3-15秒
- 比特率：128kbps
- 大小：< 1MB
- 采样率：44.1kHz

---

## 🔧 替换步骤

1. **准备音频文件**
   ```bash
   # 确保文件名正确
   mv your-jojo-audio.mp3 jojo-alert.mp3
   ```

2. **放置到项目**
   ```bash
   # 从项目根目录
   cp jojo-alert.mp3 frontend/public/jojo-alert.mp3
   ```

3. **验证文件**
   ```bash
   ls -lh frontend/public/jojo-alert.mp3
   # 应该显示文件大小
   ```

4. **重启前端**
   ```bash
   cd frontend
   npm run dev
   ```

5. **测试播放**
   - 刷新浏览器
   - 触发价格提醒
   - 应该播放自定义音频（而非Web Audio API生成的音效）

---

## 🎼 当前内置音效

如果没有自定义音频文件，系统会使用内置的Giorno's Theme旋律：

**音符序列：**
```
G4 → B4 → D5 → B4 → E5（延长）→ D5 → B4 → G4（延长）
```

**特点：**
- 基于方波合成器，模拟电子音色
- 添加低音G3和弦增强
- 每3秒循环播放一次
- 持续播放直到用户关闭提醒

---

## ⚠️ 版权说明

- 官方音频版权归原作者所有
- 仅供个人学习和非商业使用
- 如需商业用途，请购买正版授权

---

## 🎯 快速链接

**官方音源：**
- Spotify: 搜索 "Giorno's Theme"
- Apple Music: 搜索 "Il vento d'oro"

**免费素材库：**
- Freesound: https://freesound.org/
- SoundBible: http://soundbible.com/

**音频编辑工具：**
- Audacity（免费）: https://www.audacityteam.org/
- Online Audio Cutter: https://mp3cut.net/

---

完成后重启前端，即可享受真实的JOJO音效！ 🎉
