/** @typedef {{id:number,code:string,team:string,before:number|null,after:number|null,note:string}} Pair */
/** @typedef {{id:number,name:string,team:string,state:string,result:object,error:string}} Evaluation */
/** @typedef {{id:number,evaluation_id:number,decision:string,note:string,status:string}} Adoption */
/** @typedef {{id:number,evaluation_id:number,threshold:number,slots:number,state:'open'|'concluded'|'undetermined',verdict:'pass'|'fail'|'undetermined'|null,result:object,error:string}} Review */
