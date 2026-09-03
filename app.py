"""Main Streamlit application entry point."""

import streamlit as st
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="Document Query Application",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .stAlert {
        border-radius: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session
from src.components.session_manager import SessionManager
SessionManager.initialize_session()

# Page navigation
page = st.sidebar.radio(
    "Navigation",
    ["Home", "Upload", "Diagnose", "Query", "Session"],
    index=0,
)

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.markdown("### Session Info")
doc_count = SessionManager.get_document_count()
st.sidebar.metric("Documents Uploaded", doc_count)

session_duration = SessionManager.get_session_duration()
st.sidebar.write(f"Session Duration: {str(session_duration).split('.')[0]}")

# Page routing
if page == "Home":
    st.title("📖 Document Query Application")
    st.markdown("""
    ### Welcome!
    
    Upload your vehicle owner's manual and ask natural language questions to instantly find answers.
    
    **Features:**
    - 📁 Upload PDFs, images, spreadsheets, presentations, and videos
    - 🤖 AI-powered semantic search
    - ⚡ Fast, natural language answers
    - 📝 Session-based storage (automatic cleanup)
    
    **Getting Started:**
    1. Go to **Upload** page and upload a manual
    2. Go to **Query** page and ask a question
    3. Get instant answers with source attribution
    
    **Supported Formats:**
    - PDFs (.pdf)
    - Images (.png, .jpg, .jpeg, .gif) - with OCR
    - Spreadsheets (.xls, .xlsx)
    - Presentations (.ppt, .pptx)
    - Videos (.mp4, .mov, .avi, .webm)
    
    **Questions?** Check the documentation in the repository.
    """)

elif page == "Upload":
    st.title("📤 Upload Document")
    
    uploaded_file = st.file_uploader(
        "Choose a file to upload",
        type=["pdf", "png", "jpg", "jpeg", "gif", "xls", "xlsx", "ppt", "pptx", "mp4", "mov", "avi", "webm"],
        help="Supported formats: PDF, images, Excel, PowerPoint, video"
    )
    
    if uploaded_file is not None:
        st.write(f"**File:** {uploaded_file.name}")
        st.write(f"**Size:** {uploaded_file.size / 1024 / 1024:.2f} MB")
        
        if st.button("📤 Upload and Index"):
            with st.spinner("Processing..."):
                try:
                    # Read file
                    file_bytes = uploaded_file.read()
                    
                    # Validate and parse
                    from src.utils.validators import validate_file
                    from src.components.document_parser import DocumentParser
                    from src.components.embedding_generator import EmbeddingGenerator
                    import uuid
                    
                    validation_result = validate_file(uploaded_file.name, file_bytes)
                    
                    document_id = str(uuid.uuid4())
                    parser = DocumentParser()
                    
                    document = parser.parse(
                        file_bytes,
                        validation_result["filename"],
                        validation_result["file_format"],
                        document_id
                    )
                    
                    if not document.parsed_successfully:
                        st.error(f"❌ {document.parse_error_message}")
                    else:
                        # Generate embeddings
                        embedder = EmbeddingGenerator()
                        embeddings = embedder.embed_passages(document.passages)
                        
                        # Build index
                        indexer = SessionManager.get_indexer()
                        # Get all documents and passages
                        all_passages = []
                        all_embeddings = []
                        
                        for doc in SessionManager.get_documents().values():
                            if doc.parsed_successfully:
                                all_passages.extend(doc.passages)
                        
                        all_passages.extend(document.passages)
                        all_embeddings.extend(embeddings)
                        
                        if all_embeddings:
                            indexer.build_index(all_passages, all_embeddings)
                        
                        # Add to session
                        SessionManager.add_document(document)
                        
                        st.success(f"✅ {uploaded_file.name} uploaded successfully!")
                        st.write(f"**Passages extracted:** {len(document.passages)}")
                        st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

elif page == "Diagnose":
    st.title("🩺 Diagnose a Symptom")
    st.caption(
        "Stage 1 triages the symptom into likely systems and search queries, then hybrid "
        "retrieval (BM25 + vector, fused with RRF) finds the manual excerpts and diagrams "
        "used by Stage 2 to produce a differential diagnosis."
    )

    if SessionManager.get_document_count() == 0:
        st.warning("⚠️ No documents uploaded. Please upload a service manual first.")
    else:
        symptom_text = st.text_area(
            "Describe the symptom:",
            placeholder="e.g., The AC blows warm air only at highway speed and the compressor clutch won't engage.",
            help="Describe what the vehicle is doing, when it happens, and any codes/warnings.",
        )

        if st.button("🩺 Diagnose"):
            if not symptom_text.strip():
                st.warning("Please describe the symptom.")
            else:
                with st.spinner("Triaging symptom and retrieving manual excerpts..."):
                    try:
                        SessionManager.run_diagnosis(symptom_text)
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        triage = SessionManager.get_last_triage()
        diagnosis = SessionManager.get_last_diagnosis()

        if triage and diagnosis:
            # CRAG & Cross-Encoder Observability Panel
            if diagnosis.crag_report is not None:
                crag = diagnosis.crag_report
                grade_color = {
                    "CORRECT": "🟢",
                    "AMBIGUOUS": "🟡",
                    "OUT_OF_SCOPE": "🔴",
                }.get(crag.relevance_grade, "ℹ️")

                with st.expander(f"🎯 Corrective RAG (CRAG) & Cross-Encoder Observability [{grade_color} {crag.relevance_grade}]", expanded=False):
                    col_crag1, col_crag2, col_crag3 = st.columns(3)
                    with col_crag1:
                        st.metric("Relevance Grade", f"{grade_color} {crag.relevance_grade}")
                    with col_crag2:
                        st.metric("Neural Confidence", f"{crag.confidence_score:.1%}")
                    with col_crag3:
                        st.metric("Passages Retained", f"{crag.filtered_count} / {crag.original_count}")
                    
                    st.markdown(f"**2nd-Stage Reranker Model:** `{crag.reranker_model}`")
                    st.markdown("**Corrective Actions & Guardrails:**")
                    for action in crag.actions_taken:
                        st.write(f"- {action}")
                    
                    if crag.score_breakdown:
                        st.markdown("**Chunk Score Breakdown:**")
                        for item in crag.score_breakdown:
                            tag = "🖼️ [Diagram]" if item.get("is_diagram") else "📄 [Text]"
                            st.write(f"- {tag} **{item['section']}** — Score: `{item['score']:.3f}` ({item['status']})")


            with st.expander("🧠 Thinking (triage + reasoning trace)", expanded=True):
                st.markdown("**Systems identified:** " + (", ".join(triage.systems) or "—"))
                st.markdown("**Search queries:**")
                for q in triage.search_queries:
                    st.write(f"- {q}")
                if diagnosis.thinking:
                    st.markdown("**Reasoning:**")
                    st.write(diagnosis.thinking)

            st.subheader("📋 Diagnostic Steps")
            if diagnosis.steps:
                for i, step in enumerate(diagnosis.steps, 1):
                    st.write(f"{i}. {step}")
            else:
                st.info("No diagnostic steps were generated.")

            st.subheader("🔎 Differential Diagnosis")
            if diagnosis.differential:
                for cause in diagnosis.differential:
                    likelihood = cause.get("likelihood", "—")
                    st.markdown(f"**{cause.get('cause', 'Unknown cause')}** _(likelihood: {likelihood})_")
                    if cause.get("evidence"):
                        st.caption(cause["evidence"])
            else:
                st.info("No differential diagnosis could be produced from the uploaded manuals.")

            st.subheader("📚 Cited Pages")
            if diagnosis.cited_pages:
                st.write(", ".join(diagnosis.cited_pages))
            else:
                st.write("—")

            if diagnosis.diagrams:
                st.subheader("🖼️ Relevant Diagrams")
                for diagram in diagnosis.diagrams:
                    st.image(diagram["image_bytes"], caption=diagram["section"])

            st.markdown(f"**⏱️ Response time:** {diagnosis.response_time_ms} ms | **Confidence:** {diagnosis.confidence:.1%}")

            st.markdown("---")
            st.subheader("🔧 Find Nearest Service Station")
            st.caption("Stage 3: a small LLM picks the right Mapbox search category for this diagnosis, "
                       "then the Mapbox MCP server (hosted endpoint) geocodes your location, finds nearby "
                       "repair shops, and renders a map.")
            address_text = st.text_input(
                "Your location (address, city, or ZIP):",
                key="station_address_input",
                placeholder="e.g., 123 Main St, Springfield, IL",
            )
            if st.button("📍 Find nearest station"):
                if not address_text.strip():
                    st.warning("Please enter a location.")
                else:
                    with st.spinner("Searching for nearby service stations via Mapbox MCP..."):
                        try:
                            SessionManager.find_service_stations(address_text)
                        except ValueError as e:
                            st.error(f"❌ {e}")
                        except Exception as e:
                            st.error(f"❌ Location lookup failed: {e}")

            location_result = SessionManager.get_last_location_result()
            if location_result is not None:
                if location_result.error_message:
                    st.warning(location_result.error_message)
                elif location_result.stations:
                    if location_result.map_image_bytes:
                        st.image(location_result.map_image_bytes, caption=f"Stations near {location_result.query_location}")
                    for i, station in enumerate(location_result.stations, 1):
                        st.markdown(f"**{i}. {station.name}**")
                        if station.address:
                            st.caption(station.address)
                        details = []
                        if station.distance_meters is not None:
                            details.append(f"{station.distance_meters / 1609.34:.1f} mi away")
                        if station.phone:
                            details.append(f"📞 {station.phone}")
                        if station.website:
                            details.append(f"🌐 {station.website}")
                        if details:
                            st.write(" · ".join(details))
                else:
                    st.info("No nearby service stations found.")

        history = SessionManager.get_diagnosis_history()
        if history:
            st.markdown("---")
            st.subheader("📋 Diagnosis History")
            st.write(f"{len(history)} diagnosis run(s) this session.")

elif page == "Query":
    st.title("🔍 Query Documents")
    
    if SessionManager.get_document_count() == 0:
        st.warning("⚠️ No documents uploaded. Please upload a document first.")
    else:
        st.write(f"Documents: {SessionManager.get_document_count()}")
        
        query_text = st.text_input(
            "Ask a question about your documents:",
            placeholder="e.g., What's the recommended tire pressure?",
            help="Enter a natural language question"
        )
        
        if st.button("🔍 Search"):
            if not query_text.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Processing query..."):
                    try:
                        from src.components.embedding_generator import EmbeddingGenerator
                        from src.components.query_processor import QueryProcessor
                        from src.components.answer_generator import AnswerGenerator
                        import time
                        
                        start_time = time.time()
                        
                        embedder = EmbeddingGenerator()
                        indexer = SessionManager.get_indexer()
                        processor = QueryProcessor(embedder, indexer)
                        generator = AnswerGenerator()
                        
                        # Find relevant passages with 2-stage Cross-Encoder reranking & CRAG evaluation
                        passages, confidence, crag_report = processor.find_relevant_passages_with_crag(query_text)
                        
                        if not passages or (crag_report and crag_report.relevance_grade == "OUT_OF_SCOPE"):
                            st.warning("⚠️ **Corrective RAG Guardrail Triggered:** The retrieved passages have low relevance for this question. The query may be outside the scope of the uploaded manual(s).")
                            if crag_report:
                                with st.expander("🔍 CRAG Guardrail Details", expanded=False):
                                    st.write(f"- **Relevance Grade:** 🔴 {crag_report.relevance_grade}")
                                    st.write(f"- **Confidence Score:** {crag_report.confidence_score:.1%}")
                                    st.write(f"- **Reranker:** `{crag_report.reranker_model}`")
                        
                        if passages:
                            # Generate answer
                            result = generator.generate_answer(query_text, passages)
                            result.crag_report = crag_report
                            result.confidence = confidence
                            
                            elapsed = time.time() - start_time
                            
                            # Display result
                            if result.status == "success":
                                st.success("✅ Answer found!")
                                st.markdown(f"### {result.answer}")
                                
                                # CRAG Observability Expander
                                if crag_report:
                                    grade_color = {"CORRECT": "🟢", "AMBIGUOUS": "🟡", "OUT_OF_SCOPE": "🔴"}.get(crag_report.relevance_grade, "ℹ️")
                                    with st.expander(f"🎯 Corrective RAG (CRAG) & Cross-Encoder Observability [{grade_color} {crag_report.relevance_grade}]", expanded=False):
                                        col_c1, col_c2, col_c3 = st.columns(3)
                                        with col_c1:
                                            st.metric("Relevance Grade", f"{grade_color} {crag_report.relevance_grade}")
                                        with col_c2:
                                            st.metric("Neural Confidence", f"{crag_report.confidence_score:.1%}")
                                        with col_c3:
                                            st.metric("Chunks Retained", f"{crag_report.filtered_count} / {crag_report.original_count}")
                                        
                                        st.markdown(f"**2nd-Stage Reranker:** `{crag_report.reranker_model}`")
                                        for action in crag_report.actions_taken:
                                            st.write(f"- {action}")

                                st.markdown("---")
                                st.subheader("📚 Sources & Cross-Encoder Scores")
                                for source in result.sources:
                                    with st.expander(f"📄 {source['document_name']} - {source['section']}"):
                                        st.write(source['passage'])
                                
                                st.markdown(f"**⏱️ Response time:** {elapsed:.2f}s | **Confidence:** {result.confidence:.1%}")
                            else:
                                st.error(f"❌ {result.answer}")
                        
                        # Add to history
                        SessionManager.add_to_query_history({
                            "query": query_text,
                            "timestamp": datetime.now(),
                            "status": result.status if 'result' in locals() else "error",
                        })
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        # Query history
        history = SessionManager.get_query_history()
        if history:
            st.markdown("---")
            st.subheader("📋 Query History")
            for i, h in enumerate(reversed(history[-5:]), 1):
                st.write(f"{i}. {h['query']}")

elif page == "Session":
    st.title("⚙️ Session Management")
    
    st.subheader("📊 Session Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Documents", SessionManager.get_document_count())
    with col2:
        st.metric("Queries", len(SessionManager.get_query_history()))
    with col3:
        duration = SessionManager.get_session_duration()
        st.metric("Session Duration", str(duration).split('.')[0])
    
    st.markdown("---")
    st.subheader("📄 Uploaded Documents")
    documents = SessionManager.get_documents()
    if documents:
        for doc_id, doc in documents.items():
            status = "✅ Parsed" if doc.parsed_successfully else "❌ Error"
            st.write(f"{status} **{doc.filename}** ({len(doc.passages)} passages)")
    else:
        st.info("No documents uploaded yet.")
    
    st.markdown("---")
    st.subheader("🧹 Clear Session")
    if st.button("Clear All Data", key="clear_session"):
        SessionManager.clear_session()
        st.success("✅ Session cleared!")
        st.rerun()

# Footer
st.markdown("---")
st.markdown("💡 *Tip: All data is stored temporarily in your session. Data is cleared when you close this browser tab.*")
