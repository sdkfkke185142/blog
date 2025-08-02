#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import os
import sys
import requests
import threading
import time
from datetime import datetime
import csv

class TistoryContentGenerator:
    """OpenAI API를 사용한 티스토리 콘텐츠 생성 클래스"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.models_url = "https://api.openai.com/v1/models"
        self.available_models = []
    
    def get_available_models(self):
        """사용 가능한 OpenAI 모델 목록 조회"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(self.models_url, headers=headers, timeout=30)
            if response.status_code == 200:
                models_data = response.json()
                models = []
                for model in models_data['data']:
                    model_id = model['id']
                    # 채팅 완성 모델만 필터링
                    if any(keyword in model_id for keyword in ['gpt-4', 'gpt-3.5', 'gpt-4o']):
                        models.append(model_id)
                
                # 주요 모델들을 우선 순위로 정렬
                priority_models = []
                other_models = []
                
                for model in sorted(models):
                    if model in ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']:
                        priority_models.append(model)
                    else:
                        other_models.append(model)
                
                self.available_models = priority_models + other_models
                return self.available_models
            else:
                return ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo']
                
        except Exception as e:
            print(f"모델 목록 조회 오류: {e}")
            return ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo']
    
    def create_tistory_prompt(self, topic, keywords="", content_type="일반", tone="친근한"):
        """티스토리 최적화된 프롬프트 생성 (마크다운 없음)"""
        
        keyword_instruction = ""
        if keywords.strip():
            keyword_instruction = f"주요 키워드: {keywords}"
        
        prompt = f"""당신은 티스토리 블로그 전문 작성자입니다. 티스토리 플랫폼에 최적화된 글을 작성해주세요.

제목: {topic}
콘텐츠 유형: {content_type}
작성 톤: {tone}
{keyword_instruction}

티스토리 최적화 요구사항:
- 글자 수: 2000-3000자
- 일반 텍스트 형식 (마크다운 사용 금지)
- 티스토리 검색 최적화 고려
- 읽기 쉬운 문단 구성
- 네이버, 구글 SEO 최적화

구조:
1. 매력적인 제목
2. 도입부 (호기심 자극)
3. 본문 내용 (2-3개 주요 포인트)
4. 실용적인 팁이나 조언
5. 마무리 (재방문 유도)

작성 지침:
- 자연스러운 키워드 배치
- 친근하고 이해하기 쉬운 문체
- 구체적인 정보와 예시 포함
- 독자의 관심을 끝까지 유지하는 구성
- 댓글이나 공감을 유도하는 마무리

지금 위 조건에 맞는 티스토리 포스팅을 작성해주세요. 마크다운이나 HTML 태그는 사용하지 말고 순수 텍스트로만 작성해주세요."""

        return prompt
    
    def generate_content(self, topic, keywords="", content_type="일반", tone="친근한", model="gpt-4o", progress_callback=None):
        """콘텐츠 생성"""
        
        if progress_callback:
            progress_callback(10, f"프롬프트 준비 중... ({topic[:30]}...)")
        
        prompt = self.create_tistory_prompt(topic, keywords, content_type, tone)
        
        if progress_callback:
            progress_callback(30, f"AI 분석 중... ({model})")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system", 
                    "content": "당신은 티스토리 블로그 전문 작성자입니다. 마크다운이나 HTML 태그 없이 순수 텍스트로만 글을 작성합니다."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000,
            "temperature": 0.7
        }
        
        if progress_callback:
            progress_callback(50, f"콘텐츠 생성 중...")
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=120)
            
            if progress_callback:
                progress_callback(80, f"결과 처리 중...")
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # 마크다운 제거 (혹시 남아있을 경우)
                content = self.remove_markdown(content)
                
                if progress_callback:
                    progress_callback(100, f"완료!")
                
                return {
                    'success': True,
                    'content': content,
                    'char_count': len(content),
                    'word_count': len(content.split()),
                    'topic': topic,
                    'keywords': keywords,
                    'model': model
                }
            else:
                error_msg = f"API 오류: {response.status_code}"
                if response.text:
                    try:
                        error_detail = response.json().get('error', {}).get('message', response.text)
                        error_msg += f"\n상세: {error_detail}"
                    except:
                        error_msg += f"\n응답: {response.text[:200]}"
                
                return {'success': False, 'error': error_msg}
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '요청 시간 초과 (120초). 네트워크 연결을 확인하세요.'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': '네트워크 연결 오류. 인터넷 연결을 확인하세요.'}
        except Exception as e:
            return {'success': False, 'error': f'예상치 못한 오류: {str(e)}'}
    
    def remove_markdown(self, text):
        """마크다운 형식 제거"""
        import re
        
        # 헤딩 제거 (###, ##, # -> 그냥 텍스트로)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # 볼드/이탤릭 제거
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        
        # 리스트 마커 제거
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # 링크 제거 [텍스트](URL) -> 텍스트
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # 인용 제거
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
        
        # 코드 블록 제거
        text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        return text.strip()

class TistoryOptimizerApp:
    """티스토리 최적화 프로그램 GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🚀 티스토리 최적화 셋팅 프로그램")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
        
        # API 키 로드
        self.api_key = self.load_api_key()
        
        # 생성기 초기화
        if self.api_key:
            self.generator = TistoryContentGenerator(self.api_key)
            self.available_models = []
        else:
            self.generator = None
            self.available_models = []
        
        # 변수들
        self.topics_list = []
        self.results = []
        self.is_generating = False
        self.current_topic_index = 0
        self.total_topics = 0
        
        # GUI 설정
        self.setup_ui()
    
    def load_api_key(self):
        """API 키 로드"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('api_key', '')
            return ""
        except Exception as e:
            print(f"설정 파일 로드 오류: {e}")
            return ""
    
    def save_api_key(self, api_key):
        """API 키 저장"""
        try:
            config = {'api_key': api_key}
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("저장 오류", f"API 키 저장 실패: {e}")
            return False
    
    def setup_ui(self):
        """UI 설정"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 제목
        title_label = ttk.Label(main_frame, text="🚀 티스토리 최적화 셋팅 프로그램", 
                               font=("맑은 고딕", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # API 키 및 모델 설정 프레임
        config_frame = ttk.LabelFrame(main_frame, text="⚙️ API 설정", padding="10")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # API 키 설정
        ttk.Button(config_frame, text="🔑 API 키 설정", command=self.setup_api_key).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        # 모델 선택
        ttk.Label(config_frame, text="🤖 AI 모델:").grid(row=0, column=1, sticky=tk.W, padx=(20, 10))
        self.model_var = tk.StringVar(value="gpt-4o")
        self.model_combo = ttk.Combobox(config_frame, textvariable=self.model_var, state="readonly", width=25)
        self.model_combo.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # 모델 새로고침 버튼
        ttk.Button(config_frame, text="🔄 모델 새로고침", command=self.refresh_models).grid(row=0, column=3, sticky=tk.E)
        
        # 주제 입력 프레임
        topics_frame = ttk.LabelFrame(main_frame, text="📝 주제 입력 (최대 100개)", padding="10")
        topics_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        topics_frame.columnconfigure(0, weight=1)
        topics_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 주제 입력 안내
        instruction_label = ttk.Label(topics_frame, text="💡 한 줄에 하나씩 주제를 입력하세요 (Enter로 구분)")
        instruction_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # 주제 입력 텍스트 영역
        self.topics_text = scrolledtext.ScrolledText(topics_frame, wrap=tk.WORD, height=8, font=("맑은 고딕", 10))
        self.topics_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 샘플 주제 추가
        sample_topics = """재택근무 생산성 향상 방법
블로그 수익화 전략
건강한 다이어트 식단
효과적인 시간 관리법
스마트폰 사진 잘 찍는 법"""
        self.topics_text.insert(1.0, sample_topics)
        
        # 설정 프레임
        settings_frame = ttk.LabelFrame(main_frame, text="⚙️ 콘텐츠 설정", padding="10")
        settings_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(3, weight=1)
        
        # 키워드 입력
        ttk.Label(settings_frame, text="🔑 공통 키워드:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.keywords_var = tk.StringVar()
        keywords_entry = ttk.Entry(settings_frame, textvariable=self.keywords_var, font=("맑은 고딕", 10))
        keywords_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 20))
        keywords_entry.insert(0, "티스토리, 블로그")
        
        # 콘텐츠 유형
        ttk.Label(settings_frame, text="📝 콘텐츠 유형:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.content_type_var = tk.StringVar(value="일반")
        content_type_combo = ttk.Combobox(settings_frame, textvariable=self.content_type_var,
                                         values=["일반", "정보성", "리뷰", "가이드", "뉴스", "경험담"], state="readonly")
        content_type_combo.grid(row=0, column=3, sticky=(tk.W, tk.E))
        
        # 작성 톤
        ttk.Label(settings_frame, text="🎭 작성 톤:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.tone_var = tk.StringVar(value="친근한")
        tone_combo = ttk.Combobox(settings_frame, textvariable=self.tone_var,
                                 values=["친근한", "전문적", "유머러스", "감성적", "중립적"], state="readonly")
        tone_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 0), padx=(0, 20))
        
        # 생성 제한
        ttk.Label(settings_frame, text="📊 생성 개수:").grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.limit_var = tk.StringVar(value="100")
        limit_entry = ttk.Entry(settings_frame, textvariable=self.limit_var, width=10)
        limit_entry.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        # 제어 버튼 프레임
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=4, column=0, columnspan=3, pady=(20, 10), sticky=(tk.W, tk.E))
        
        # 생성 시작 버튼
        self.generate_button = ttk.Button(control_frame, text="🚀 일괄 생성 시작", 
                                         command=self.start_batch_generation, 
                                         style="Accent.TButton")
        self.generate_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 중지 버튼
        self.stop_button = ttk.Button(control_frame, text="⏹️ 중지", 
                                     command=self.stop_generation, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 결과 내보내기 버튼
        self.export_button = ttk.Button(control_frame, text="💾 결과 내보내기", 
                                       command=self.export_results, state="disabled")
        self.export_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 일괄다운로드 버튼
        self.bulk_download_button = ttk.Button(control_frame, text="📝 일괄다운로드 (메모장)", 
                                             command=self.bulk_download_to_notepad, state="disabled")
        self.bulk_download_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # HTML 다운로드 버튼
        self.html_download_button = ttk.Button(control_frame, text="🌐 HTML 다운로드", 
                                             command=self.bulk_download_to_html, state="disabled")
        self.html_download_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 전체 삭제 버튼
        ttk.Button(control_frame, text="🗑️ 전체 삭제", command=self.clear_all).pack(side=tk.RIGHT)
        
        # 진행 상황 표시
        progress_frame = ttk.LabelFrame(main_frame, text="📊 진행 상황", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.StringVar(value="생성 시작 버튼을 클릭하여 시작하세요.")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 현재 진행률 표시
        self.current_progress_var = tk.StringVar(value="대기 중...")
        self.current_progress_label = ttk.Label(progress_frame, textvariable=self.current_progress_var, 
                                               font=("맑은 고딕", 9))
        self.current_progress_label.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        # 결과 표시 프레임
        result_frame = ttk.LabelFrame(main_frame, text="📋 생성 결과", padding="10")
        result_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=2)
        
        # 결과 리스트
        self.result_tree = ttk.Treeview(result_frame, columns=('주제', '상태', '글자수', '모델', '시간'), show='headings', height=6)
        self.result_tree.heading('주제', text='주제')
        self.result_tree.heading('상태', text='상태')
        self.result_tree.heading('글자수', text='글자수')
        self.result_tree.heading('모델', text='모델')
        self.result_tree.heading('시간', text='생성시간')
        
        self.result_tree.column('주제', width=300)
        self.result_tree.column('상태', width=100)
        self.result_tree.column('글자수', width=80)
        self.result_tree.column('모델', width=120)
        self.result_tree.column('시간', width=150)
        
        self.result_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.result_tree.configure(yscrollcommand=scrollbar.set)
        
        # 결과 상세보기
        self.result_tree.bind('<Double-1>', self.show_content_detail)
        
        # 초기 설정
        if not self.api_key:
            self.progress_var.set("⚠️ API 키를 설정해주세요.")
            self.generate_button.config(state="disabled")
        else:
            self.refresh_models()
    
    def setup_api_key(self):
        """API 키 설정 다이얼로그"""
        dialog = tk.Toplevel(self.root)
        dialog.title("API 키 설정")
        dialog.geometry("500x250")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 중앙 배치
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="OpenAI API 키를 입력하세요:", 
                 font=("맑은 고딕", 12, "bold")).pack(pady=(0, 10))
        
        api_key_var = tk.StringVar(value=self.api_key)
        api_entry = ttk.Entry(frame, textvariable=api_key_var, show="*", width=60, font=("맑은 고딕", 10))
        api_entry.pack(pady=(0, 10), fill=tk.X)
        api_entry.focus()
        
        ttk.Label(frame, text="https://platform.openai.com/api-keys 에서 발급받을 수 있습니다.", 
                 foreground="gray").pack(pady=(0, 10))
        
        ttk.Label(frame, text="API 키가 설정되면 사용 가능한 AI 모델 목록을 자동으로 불러옵니다.", 
                 foreground="blue").pack(pady=(0, 20))
        
        def save_and_close():
            new_key = api_key_var.get().strip()
            if new_key:
                if self.save_api_key(new_key):
                    self.api_key = new_key
                    self.generator = TistoryContentGenerator(new_key)
                    self.progress_var.set("API 키가 설정되었습니다. 모델을 불러오는 중...")
                    self.generate_button.config(state="normal")
                    dialog.destroy()
                    messagebox.showinfo("성공", "API 키가 저장되었습니다!")
                    self.refresh_models()
            else:
                messagebox.showwarning("입력 오류", "API 키를 입력해주세요.")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="저장", command=save_and_close).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="취소", command=dialog.destroy).pack(side=tk.RIGHT)
        
        api_entry.bind('<Return>', lambda e: save_and_close())
    
    def refresh_models(self):
        """AI 모델 목록 새로고침"""
        if not self.generator:
            return
        
        def fetch_models():
            try:
                models = self.generator.get_available_models()
                self.root.after(0, lambda: self.update_model_list(models))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("오류", f"모델 목록 조회 실패: {e}"))
        
        thread = threading.Thread(target=fetch_models)
        thread.daemon = True
        thread.start()
    
    def update_model_list(self, models):
        """모델 리스트 업데이트"""
        self.available_models = models
        self.model_combo['values'] = models
        if models and self.model_var.get() not in models:
            self.model_var.set(models[0])
        self.progress_var.set(f"사용 가능한 모델 {len(models)}개를 불러왔습니다.")
    
    def start_batch_generation(self):
        """일괄 생성 시작"""
        # 주제 파싱
        topics_text = self.topics_text.get(1.0, tk.END).strip()
        if not topics_text:
            messagebox.showwarning("입력 오류", "주제를 입력해주세요.")
            return
        
        # 주제 리스트 생성
        self.topics_list = [topic.strip() for topic in topics_text.split('\n') if topic.strip()]
        
        # 제한 개수 확인
        try:
            limit = int(self.limit_var.get())
            if limit <= 0:
                limit = 100
        except:
            limit = 100
        
        self.topics_list = self.topics_list[:limit]
        
        if not self.topics_list:
            messagebox.showwarning("입력 오류", "유효한 주제가 없습니다.")
            return
        
        if not self.generator:
            messagebox.showerror("설정 오류", "API 키를 먼저 설정해주세요.")
            return
        
        # 초기화
        self.results = []
        self.is_generating = True
        self.current_topic_index = 0
        self.total_topics = len(self.topics_list)
        
        # UI 상태 변경
        self.generate_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.export_button.config(state="disabled")
        
        # 결과 트리 초기화
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # 진행률 초기화
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = self.total_topics
        
        # 별도 스레드에서 생성 시작
        thread = threading.Thread(target=self._batch_generation_thread)
        thread.daemon = True
        thread.start()
    
    def _batch_generation_thread(self):
        """일괄 생성 스레드"""
        start_time = datetime.now()
        
        for i, topic in enumerate(self.topics_list):
            if not self.is_generating:
                break
            
            self.current_topic_index = i + 1
            
            # UI 업데이트
            self.root.after(0, self._update_progress, 
                          f"진행 중: {self.current_topic_index}/{self.total_topics} - {topic[:30]}...")
            
            try:
                # 콘텐츠 생성
                result = self.generator.generate_content(
                    topic=topic,
                    keywords=self.keywords_var.get(),
                    content_type=self.content_type_var.get(),
                    tone=self.tone_var.get(),
                    model=self.model_var.get(),
                    progress_callback=None
                )
                
                # 결과 저장
                result_item = {
                    'topic': topic,
                    'result': result,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                self.results.append(result_item)
                
                # UI 업데이트
                self.root.after(0, self._add_result_to_tree, result_item)
                self.root.after(0, self._update_progress_bar, i + 1)
                
                # 요청 간 지연 (API 제한 고려)
                time.sleep(1)
                
            except Exception as e:
                error_result = {
                    'topic': topic,
                    'result': {'success': False, 'error': str(e)},
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                self.results.append(error_result)
                self.root.after(0, self._add_result_to_tree, error_result)
                self.root.after(0, self._update_progress_bar, i + 1)
        
        # 완료 처리
        end_time = datetime.now()
        elapsed = end_time - start_time
        
        if self.is_generating:
            self.root.after(0, self._generation_complete, elapsed)
        else:
            self.root.after(0, self._generation_stopped)
    
    def _update_progress(self, message):
        """진행 상황 업데이트"""
        self.current_progress_var.set(message)
    
    def _update_progress_bar(self, value):
        """진행률 바 업데이트"""
        self.progress_bar['value'] = value
    
    def _add_result_to_tree(self, result_item):
        """결과를 트리뷰에 추가"""
        topic = result_item['topic']
        result = result_item['result']
        timestamp = result_item['timestamp']
        
        if result['success']:
            status = "✅ 완료"
            char_count = f"{result['char_count']:,}자"
            model = result.get('model', 'N/A')
        else:
            status = "❌ 실패"
            char_count = "0자"
            model = "N/A"
        
        self.result_tree.insert('', 'end', values=(
            topic[:50] + "..." if len(topic) > 50 else topic,
            status,
            char_count,
            model,
            timestamp
        ))
        
        # 자동 스크롤
        self.result_tree.see(self.result_tree.get_children()[-1])
    
    def _generation_complete(self, elapsed):
        """생성 완료 처리"""
        self.is_generating = False
        
        # UI 상태 변경
        self.generate_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.export_button.config(state="normal")
        self.bulk_download_button.config(state="normal")
        self.html_download_button.config(state="normal")
        
        # 통계 계산
        success_count = sum(1 for r in self.results if r['result']['success'])
        fail_count = len(self.results) - success_count
        
        total_chars = sum(r['result'].get('char_count', 0) for r in self.results if r['result']['success'])
        
        message = f"✅ 완료! 성공: {success_count}, 실패: {fail_count}, 총 {total_chars:,}자 생성 (소요시간: {elapsed})"
        self.progress_var.set(message)
        self.current_progress_var.set("작업 완료")
        
        messagebox.showinfo("완료", f"일괄 생성이 완료되었습니다!\n\n성공: {success_count}개\n실패: {fail_count}개\n총 글자수: {total_chars:,}자\n소요시간: {elapsed}")
    
    def _generation_stopped(self):
        """생성 중지 처리"""
        self.is_generating = False
        
        # UI 상태 변경
        self.generate_button.config(state="normal")
        self.stop_button.config(state="disabled")
        if self.results:
            self.export_button.config(state="normal")
            self.bulk_download_button.config(state="normal")
            self.html_download_button.config(state="normal")
        
        self.progress_var.set("⏹️ 사용자에 의해 중지되었습니다.")
        self.current_progress_var.set("중지됨")
    
    def stop_generation(self):
        """생성 중지"""
        if self.is_generating:
            self.is_generating = False
            self.progress_var.set("⏹️ 중지 중...")
    
    def show_content_detail(self, event):
        """콘텐츠 상세보기"""
        selection = self.result_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        item_index = self.result_tree.index(item_id)
        
        if item_index < len(self.results):
            result_item = self.results[item_index]
            
            # 상세보기 창
            detail_window = tk.Toplevel(self.root)
            detail_window.title(f"상세보기: {result_item['topic'][:30]}...")
            detail_window.geometry("800x600")
            detail_window.transient(self.root)
            
            frame = ttk.Frame(detail_window, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # 제목 및 정보
            info_frame = ttk.Frame(frame)
            info_frame.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(info_frame, text=f"주제: {result_item['topic']}", 
                     font=("맑은 고딕", 12, "bold")).pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"생성 시간: {result_item['timestamp']}", 
                     foreground="gray").pack(anchor=tk.W)
            
            if result_item['result']['success']:
                result = result_item['result']
                ttk.Label(info_frame, text=f"글자수: {result['char_count']:,}자, 단어수: {result['word_count']:,}개, 모델: {result.get('model', 'N/A')}", 
                         foreground="blue").pack(anchor=tk.W)
                
                # 콘텐츠 표시
                content_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("맑은 고딕", 10))
                content_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
                content_text.insert(1.0, result['content'])
                content_text.config(state="disabled")
                
                # 복사 버튼
                def copy_content():
                    detail_window.clipboard_clear()
                    detail_window.clipboard_append(result['content'])
                    messagebox.showinfo("복사", "클립보드에 복사되었습니다!")
                
                ttk.Button(frame, text="📋 복사", command=copy_content).pack(side=tk.LEFT)
            else:
                ttk.Label(info_frame, text=f"오류: {result_item['result']['error']}", 
                         foreground="red").pack(anchor=tk.W)
            
            ttk.Button(frame, text="닫기", command=detail_window.destroy).pack(side=tk.RIGHT)
    
    def export_results(self):
        """결과 내보내기"""
        if not self.results:
            messagebox.showwarning("내보내기 오류", "내보낼 결과가 없습니다.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 파일", "*.csv"), ("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
            initialvalue=f"tistory_contents_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        if filename:
            try:
                if filename.endswith('.csv'):
                    self._export_csv(filename)
                else:
                    self._export_txt(filename)
                messagebox.showinfo("내보내기 완료", f"결과가 저장되었습니다:\n{filename}")
            except Exception as e:
                messagebox.showerror("내보내기 오류", f"파일 저장 중 오류가 발생했습니다:\n{e}")
    
    def _export_csv(self, filename):
        """CSV 형식으로 내보내기"""
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['주제', '상태', '글자수', '단어수', '모델', '생성시간', '콘텐츠', '오류메시지'])
            
            for item in self.results:
                topic = item['topic']
                result = item['result']
                timestamp = item['timestamp']
                
                if result['success']:
                    writer.writerow([
                        topic,
                        '성공',
                        result['char_count'],
                        result['word_count'],
                        result.get('model', ''),
                        timestamp,
                        result['content'],
                        ''
                    ])
                else:
                    writer.writerow([
                        topic,
                        '실패',
                        0,
                        0,
                        '',
                        timestamp,
                        '',
                        result['error']
                    ])
    
    def _export_txt(self, filename):
        """텍스트 형식으로 내보내기"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 티스토리 콘텐츠 생성 결과\n\n")
            f.write(f"생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"총 {len(self.results)}개 주제 처리\n\n")
            
            success_count = sum(1 for r in self.results if r['result']['success'])
            f.write(f"성공: {success_count}개, 실패: {len(self.results) - success_count}개\n\n")
            f.write("=" * 80 + "\n\n")
            
            for i, item in enumerate(self.results, 1):
                topic = item['topic']
                result = item['result']
                timestamp = item['timestamp']
                
                f.write(f"[{i}] {topic}\n")
                f.write(f"생성시간: {timestamp}\n")
                
                if result['success']:
                    f.write(f"상태: 성공 ({result['char_count']:,}자, {result['word_count']:,}단어)\n")
                    f.write(f"모델: {result.get('model', 'N/A')}\n")
                    f.write("\n내용:\n")
                    f.write("-" * 60 + "\n")
                    f.write(result['content'])
                    f.write("\n" + "-" * 60 + "\n\n")
                else:
                    f.write(f"상태: 실패\n")
                    f.write(f"오류: {result['error']}\n\n")
                
                f.write("=" * 80 + "\n\n")
    
    def bulk_download_to_notepad(self):
        """모든 글을 하나의 메모장 파일로 일괄 다운로드"""
        if not self.results:
            messagebox.showwarning("다운로드 오류", "다운로드할 결과가 없습니다.")
            return
        
        # 성공한 결과만 필터링
        successful_results = [item for item in self.results if item['result']['success']]
        
        if not successful_results:
            messagebox.showwarning("다운로드 오류", "다운로드할 성공한 결과가 없습니다.")
            return
        
        # 바탕화면 경로 가져오기
        import os
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        
        # 파일 이름 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(desktop_path, f"티스토리_블로그_전체글_{timestamp}.txt")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # 헤더 작성
                f.write("="*80 + "\n")
                f.write("              티스토리 블로그 전체 글 모음\n")
                f.write("="*80 + "\n\n")
                f.write(f"생성 일시: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}\n")
                f.write(f"총 글 개수: {len(successful_results)}개\n")
                
                total_chars = sum(item['result']['char_count'] for item in successful_results)
                f.write(f"총 글자수: {total_chars:,}자\n\n")
                
                f.write("="*80 + "\n\n")
                
                # 각 글 작성
                for i, item in enumerate(successful_results, 1):
                    topic = item['topic']
                    result = item['result']
                    timestamp = item['timestamp']
                    
                    # 글 번호와 제목
                    f.write(f"\n\n[{i:03d}] {topic}\n")
                    f.write("-" * len(f"[{i:03d}] {topic}") + "\n")
                    f.write(f"작성일: {timestamp}\n")
                    f.write(f"글자수: {result['char_count']:,}자\n")
                    f.write(f"AI 모델: {result.get('model', 'N/A')}\n\n")
                    
                    # 본문 내용
                    content = result['content'].strip()
                    f.write(content)
                    f.write("\n\n")
                    f.write("●" * 60)
                    f.write("\n")
                
                # 푸터
                f.write("\n\n" + "="*80 + "\n")
                f.write("                        작성 완료\n")
                f.write("="*80 + "\n")
                f.write(f"\n파일 생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("티스토리 최적화 프로그램으로 생성됨\n")
                
            # 성공 메시지
            messagebox.showinfo(
                "다운로드 완료", 
                f"모든 글이 성공적으로 다운로드되었습니다!\n\n"
                f"파일 위치: {filename}\n"
                f"글 개수: {len(successful_results)}개\n"
                f"총 글자수: {total_chars:,}자\n\n"
                f"바탕화면에서 확인하세요!"
            )
            
            # 파일 열기 여부 확인
            if messagebox.askyesno("파일 열기", "생성된 파일을 지금 열어보시겠습니까?"):
                try:
                    import subprocess
                    subprocess.run(['notepad.exe', filename], check=True)
                except Exception as e:
                    # notepad가 실행되지 않으면 기본 프로그램으로 열기
                    try:
                        os.startfile(filename)
                    except Exception as e2:
                        messagebox.showwarning("파일 열기 실패", f"파일을 열 수 없습니다: {e2}")
                        
        except Exception as e:
            messagebox.showerror("다운로드 오류", f"파일 저장 중 오류가 발생했습니다:\n{e}")
    
    def bulk_download_to_html(self):
        """모든 글을 HTML 형식으로 일괄 다운로드"""
        if not self.results:
            messagebox.showwarning("다운로드 오류", "다운로드할 결과가 없습니다.")
            return
        
        # 성공한 결과만 필터링
        successful_results = [item for item in self.results if item['result']['success']]
        
        if not successful_results:
            messagebox.showwarning("다운로드 오류", "다운로드할 성공한 결과가 없습니다.")
            return
        
        # 바탕화면 경로 가져오기
        import os
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        
        # 파일 이름 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(desktop_path, f"티스토리_블로그_전체글_{timestamp}.html")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                total_chars = sum(item['result']['char_count'] for item in successful_results)
                
                # HTML 문서 시작
                f.write("""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>티스토리 블로그 전체 글 모음</title>
    <style>
        body {
            font-family: 'Malgun Gothic', '맑은 고딕', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #007bff;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .header .stats {
            color: #666;
            font-size: 1.1em;
        }
        .post {
            margin-bottom: 40px;
            padding: 25px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            background-color: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .post-header {
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        .post-title {
            color: #007bff;
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .post-meta {
            color: #666;
            font-size: 0.9em;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .post-content {
            white-space: pre-line;
            line-height: 1.8;
            font-size: 1.1em;
        }
        .post-number {
            background: #007bff;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-weight: bold;
            display: inline-block;
            margin-bottom: 10px;
        }
        .toc {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }
        .toc h2 {
            color: #007bff;
            margin-top: 0;
            margin-bottom: 15px;
        }
        .toc ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .toc li {
            padding: 5px 0;
            border-bottom: 1px solid #dee2e6;
        }
        .toc li:last-child {
            border-bottom: none;
        }
        .toc a {
            color: #007bff;
            text-decoration: none;
        }
        .toc a:hover {
            text-decoration: underline;
        }
        .footer {
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #e9ecef;
            color: #666;
        }
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            .container {
                padding: 20px;
            }
            .post {
                padding: 15px;
            }
            .post-title {
                font-size: 1.5em;
            }
        }
        @media print {
            body {
                background-color: white;
            }
            .container {
                box-shadow: none;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📝 티스토리 블로그 전체 글 모음</h1>
            <div class="stats">""")
                
                f.write(f"""
                <strong>생성 일시:</strong> {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}<br>
                <strong>총 글 개수:</strong> {len(successful_results):,}개<br>
                <strong>총 글자수:</strong> {total_chars:,}자
            </div>
        </div>
        
        <!-- 목차 -->
        <div class="toc">
            <h2>📋 목차</h2>
            <ul>""")
                
                # 목차 생성
                for i, item in enumerate(successful_results, 1):
                    topic = item['topic']
                    f.write(f'                <li><a href="#post-{i}">[{i:03d}] {topic}</a></li>\n')
                
                f.write("""            </ul>
        </div>
        
        <!-- 본문 -->""")
                
                # 각 글 작성
                for i, item in enumerate(successful_results, 1):
                    topic = item['topic']
                    result = item['result']
                    timestamp = item['timestamp']
                    
                    # HTML 특수문자 이스케이프
                    def escape_html(text):
                        import html
                        return html.escape(text)
                    
                    escaped_topic = escape_html(topic)
                    escaped_content = escape_html(result['content'].strip())
                    
                    f.write(f"""
        <div class="post" id="post-{i}">
            <div class="post-header">
                <div class="post-number">{i:03d}</div>
                <div class="post-title">{escaped_topic}</div>
                <div class="post-meta">
                    <span>📅 작성일: {timestamp}</span>
                    <span>📊 글자수: {result['char_count']:,}자</span>
                    <span>🤖 AI 모델: {result.get('model', 'N/A')}</span>
                </div>
            </div>
            <div class="post-content">{escaped_content}</div>
        </div>""")
                
                # HTML 문서 마무리
                f.write(f"""
        
        <div class="footer">
            <p><strong>파일 생성:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>🚀 티스토리 최적화 프로그램으로 생성됨</p>
        </div>
    </div>
</body>
</html>""")
                
            # 성공 메시지
            messagebox.showinfo(
                "HTML 다운로드 완료", 
                f"모든 글이 HTML 형식으로 다운로드되었습니다!\n\n"
                f"파일 위치: {filename}\n"
                f"글 개수: {len(successful_results)}개\n"
                f"총 글자수: {total_chars:,}자\n\n"
                f"바탕화면에서 확인하세요!"
            )
            
            # 파일 열기 여부 확인
            if messagebox.askyesno("파일 열기", "생성된 HTML 파일을 브라우저에서 열어보시겠습니까?"):
                try:
                    import webbrowser
                    webbrowser.open('file://' + filename.replace('\\', '/'))
                except Exception as e:
                    try:
                        os.startfile(filename)
                    except Exception as e2:
                        messagebox.showwarning("파일 열기 실패", f"파일을 열 수 없습니다: {e2}")
                        
        except Exception as e:
            messagebox.showerror("다운로드 오류", f"HTML 파일 저장 중 오류가 발생했습니다:\n{e}")
    
    def clear_all(self):
        """전체 삭제"""
        if messagebox.askyesno("확인", "모든 결과를 삭제하시겠습니까?"):
            # 진행 중인 작업 중지
            if self.is_generating:
                self.stop_generation()
            
            # 데이터 초기화
            self.results = []
            self.topics_list = []
            
            # UI 초기화
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            
            self.progress_bar['value'] = 0
            self.progress_var.set("삭제되었습니다.")
            self.current_progress_var.set("대기 중...")
            self.export_button.config(state="disabled")
            self.bulk_download_button.config(state="disabled")
            self.html_download_button.config(state="disabled")
    
    def run(self):
        """애플리케이션 실행"""
        self.root.mainloop()

def main():
    """메인 함수"""
    try:
        app = TistoryOptimizerApp()
        app.run()
    except Exception as e:
        print(f"애플리케이션 실행 오류: {e}")
        messagebox.showerror("오류", f"애플리케이션 실행 중 오류가 발생했습니다:\n{e}")

if __name__ == "__main__":
    main()