--
-- PostgreSQL database dump
--

\restrict FeGD4O2uDApdumldMxv1Y2sYPyqZllXgtyDsNNMh2EeQwQqXvPWaXXuO8gzTddN

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: adoptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.adoptions (
    id integer NOT NULL,
    evaluation_id integer,
    decision character varying(30),
    note text,
    status character varying(20)
);


--
-- Name: adoptions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.adoptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: adoptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.adoptions_id_seq OWNED BY public.adoptions.id;


--
-- Name: audits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audits (
    id integer NOT NULL,
    actor character varying(100),
    action character varying(200),
    created character varying(40)
);


--
-- Name: audits_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audits_id_seq OWNED BY public.audits.id;


--
-- Name: evaluations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evaluations (
    id integer NOT NULL,
    name character varying(100),
    team character varying(40),
    state character varying(20),
    result json,
    error text
);


--
-- Name: evaluations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.evaluations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evaluations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.evaluations_id_seq OWNED BY public.evaluations.id;


--
-- Name: pairs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pairs (
    id integer NOT NULL,
    code character varying(60) NOT NULL,
    team character varying(40),
    before double precision,
    after double precision,
    note text
);


--
-- Name: pairs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pairs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pairs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pairs_id_seq OWNED BY public.pairs.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(100) NOT NULL,
    password character varying(200),
    role character varying(20)
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: adoptions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adoptions ALTER COLUMN id SET DEFAULT nextval('public.adoptions_id_seq'::regclass);


--
-- Name: audits id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audits ALTER COLUMN id SET DEFAULT nextval('public.audits_id_seq'::regclass);


--
-- Name: evaluations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluations ALTER COLUMN id SET DEFAULT nextval('public.evaluations_id_seq'::regclass);


--
-- Name: pairs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pairs ALTER COLUMN id SET DEFAULT nextval('public.pairs_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: adoptions adoptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adoptions
    ADD CONSTRAINT adoptions_pkey PRIMARY KEY (id);


--
-- Name: audits audits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audits
    ADD CONSTRAINT audits_pkey PRIMARY KEY (id);


--
-- Name: evaluations evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluations
    ADD CONSTRAINT evaluations_pkey PRIMARY KEY (id);


--
-- Name: pairs pairs_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pairs
    ADD CONSTRAINT pairs_code_key UNIQUE (code);


--
-- Name: pairs pairs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pairs
    ADD CONSTRAINT pairs_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: adoptions adoptions_evaluation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adoptions
    ADD CONSTRAINT adoptions_evaluation_id_fkey FOREIGN KEY (evaluation_id) REFERENCES public.evaluations(id);


--
-- Name: reviews / review_tasks / pair_corrections; Type: TABLE; Schema: public; Owner: -
-- 缺测复核：冻结名单与已知分，按缺项可达取值计算全员平均改善区间，并按名额派补查。
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    evaluation_id integer NOT NULL,
    threshold double precision NOT NULL,
    slots integer NOT NULL,
    state character varying(20),
    verdict character varying(20),
    error text,
    result json
);

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;
ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);
ALTER TABLE ONLY public.reviews ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_evaluation_id_fkey FOREIGN KEY (evaluation_id) REFERENCES public.evaluations(id);

CREATE TABLE public.review_tasks (
    id integer NOT NULL,
    review_id integer NOT NULL,
    code character varying(60) NOT NULL,
    team character varying(40),
    missing character varying(20) NOT NULL,
    state character varying(20),
    dispatch_key character varying(120) NOT NULL,
    request_key character varying(120),
    slot_no integer,
    attempts integer,
    created character varying(40),
    updated character varying(40),
    note text
);

CREATE SEQUENCE public.review_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.review_tasks_id_seq OWNED BY public.review_tasks.id;
ALTER TABLE ONLY public.review_tasks ALTER COLUMN id SET DEFAULT nextval('public.review_tasks_id_seq'::regclass);
ALTER TABLE ONLY public.review_tasks ADD CONSTRAINT review_tasks_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.review_tasks
    ADD CONSTRAINT review_tasks_unique_dispatch UNIQUE (review_id, dispatch_key);
ALTER TABLE ONLY public.review_tasks
    ADD CONSTRAINT review_tasks_unique_slot UNIQUE (review_id, slot_no);
ALTER TABLE ONLY public.review_tasks
    ADD CONSTRAINT review_tasks_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.reviews(id);

CREATE TABLE public.pair_corrections (
    id integer NOT NULL,
    review_id integer,
    pair_id integer NOT NULL,
    code character varying(60),
    field character varying(10),
    old_value double precision,
    new_value double precision,
    source character varying(120),
    actor character varying(100),
    created character varying(40),
    late boolean
);

CREATE SEQUENCE public.pair_corrections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.pair_corrections_id_seq OWNED BY public.pair_corrections.id;
ALTER TABLE ONLY public.pair_corrections ALTER COLUMN id SET DEFAULT nextval('public.pair_corrections_id_seq'::regclass);
ALTER TABLE ONLY public.pair_corrections ADD CONSTRAINT pair_corrections_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.pair_corrections
    ADD CONSTRAINT pair_corrections_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.reviews(id);
ALTER TABLE ONLY public.pair_corrections
    ADD CONSTRAINT pair_corrections_pair_id_fkey FOREIGN KEY (pair_id) REFERENCES public.pairs(id);

--
-- PostgreSQL database dump complete
--

\unrestrict FeGD4O2uDApdumldMxv1Y2sYPyqZllXgtyDsNNMh2EeQwQqXvPWaXXuO8gzTddN

